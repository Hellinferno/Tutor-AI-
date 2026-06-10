from __future__ import annotations

import random
import re

from .models import AnswerKey, Citation, Quiz, QuizQuestion
from .rag import RagEngine
from .store import InMemoryStudyLabStore
from .text_processing import tokenize


class QuizEngine:
    def __init__(self, store: InMemoryStudyLabStore, rag: RagEngine) -> None:
        self.store = store
        self.rag = rag

    def generate_quiz(
        self,
        notebook_id: str,
        num_questions: int = 5,
        question_types: list[str] | None = None,
        topic: str | None = None,
    ) -> Quiz:
        self.store.require_notebook(notebook_id)
        guides = self.store.notebook_guides(notebook_id)
        chunks = self.store.notebook_chunks(notebook_id)

        if not guides and not chunks and not topic:
            raise ValueError("Cannot generate quiz: notebook has no sources or guides.")

        types = question_types or ["mcq", "true_false", "short_answer"]
        questions: list[QuizQuestion] = []
        all_concepts = []
        for guide in guides:
            all_concepts.extend(guide.key_concepts)
        if topic:
            all_concepts.extend(tokenize(topic) or [topic])
        all_concepts = list(dict.fromkeys(all_concepts))

        sentences = []
        for chunk in chunks:
            sentences.extend(re.split(r"(?<=[.!?])\s+", chunk.text))

        for i in range(num_questions):
            q_type = types[i % len(types)]
            if q_type == "mcq" and chunks:
                q = self._make_mcq(chunks, all_concepts, i)
            elif q_type == "mcq":
                q = self._make_topic_mcq(topic or "core concept", all_concepts or [topic or "core concept"], i)
            elif q_type == "true_false" and sentences:
                q = self._make_true_false(sentences, all_concepts, i)
            elif q_type == "true_false":
                q = self._make_topic_true_false(topic or "core concept", i)
            elif q_type == "short_answer" and all_concepts:
                q = self._make_short_answer(all_concepts, chunks, i, guides)
            else:
                q = self._make_short_answer(all_concepts or ["core concepts"], chunks, i, guides)
            questions.append(q)

        notebook = self.store.require_notebook(notebook_id)
        quiz = Quiz(
            id=self.store.next_id("quiz"),
            notebook_id=notebook_id,
            title=f"{notebook.title} - Quiz",
            questions=questions,
            topic=topic,
        )
        return self.store.add_quiz(quiz)

    def generate_answer_key(self, quiz_id: str) -> AnswerKey:
        quiz = self.store.require_quiz(quiz_id)
        answers = []
        for q in quiz.questions:
            verified, method = self._verify_question_key(q)
            answers.append({
                "question_id": q.id,
                "correct_answer": q.correct_answer,
                "question_text": q.question_text,
                "type": q.type,
                "options": q.options,
                "points": q.points,
                "verified": verified,
                "verification_method": method,
                "citations": [asdict_safe(c) for c in (q.citations or [])],
            })
        key = AnswerKey(
            id=self.store.next_id("answer_key"),
            source_id=quiz_id,
            source_type="quiz",
            answers=answers,
            verified=all(answer["verified"] for answer in answers),
            verification_method="deterministic_source_check",
        )
        return self.store.add_answer_key(key)

    def get_quiz(self, quiz_id: str, include_answers: bool = False) -> Quiz:
        quiz = self.store.require_quiz(quiz_id)
        if not include_answers:
            hidden = []
            for q in quiz.questions:
                hidden.append(QuizQuestion(
                    id=q.id,
                    type=q.type,
                    question_text=q.question_text,
                    correct_answer="",
                    points=q.points,
                    difficulty=q.difficulty,
                    options=q.options,
                    citations=None,
                ))
            return Quiz(
                id=quiz.id,
                notebook_id=quiz.notebook_id,
                title=quiz.title,
                questions=hidden,
                topic=quiz.topic,
            )
        return quiz

    def _make_mcq(self, chunks: list, concepts: list[str], seed: int) -> QuizQuestion:
        rng = random.Random(seed)
        source_chunk = chunks[seed % len(chunks)]
        text = source_chunk.text.strip()
        question_text = f"Based on your sources, which statement best describes the material?"
        correct = text[:200].strip()
        distractors = [c for c in concepts if c.lower() not in correct.lower()]
        rng.shuffle(distractors)
        options = [correct[:80]] + [d[:80] for d in distractors[:3]]
        while len(options) < 4:
            options.append(f"None of the above")
        rng.shuffle(options)
        return QuizQuestion(
            id=self.store.next_id("q"),
            type="mcq",
            question_text=question_text,
            correct_answer=correct[:80],
            points=2,
            options=options,
            citations=[Citation(
                source_id=getattr(source_chunk, "source_id", ""),
                source_title="",
                chunk_index=getattr(source_chunk, "chunk_index", 0),
                start_char=getattr(source_chunk, "start_char", 0),
                end_char=getattr(source_chunk, "end_char", 0),
                snippet=correct[:240],
                score=1.0,
            )],
        )

    def _make_topic_mcq(self, topic: str, concepts: list[str], seed: int) -> QuizQuestion:
        rng = random.Random(seed)
        concept = concepts[seed % len(concepts)]
        correct = f"{concept} is a key concept within {topic}."
        options = [
            correct,
            f"{concept} is unrelated to {topic}.",
            f"{topic} cannot be studied with examples.",
            "None of the above",
        ]
        rng.shuffle(options)
        return QuizQuestion(
            id=self.store.next_id("q"),
            type="mcq",
            question_text=f"Which statement best fits the topic '{topic}'?",
            correct_answer=correct,
            points=2,
            options=options,
        )

    def _make_topic_true_false(self, topic: str, seed: int) -> QuizQuestion:
        is_true = seed % 2 == 0
        statement = f"{topic} can be studied through definitions, examples, and practice questions."
        if not is_true:
            statement = f"{topic} should never be connected to examples or practice."
        return QuizQuestion(
            id=self.store.next_id("q"),
            type="true_false",
            question_text=f"True or False: {statement}",
            correct_answer="True" if is_true else "False",
            points=1,
            options=["True", "False"],
        )

    def _make_true_false(self, sentences: list[str], concepts: list[str], seed: int) -> QuizQuestion:
        rng = random.Random(seed + 100)
        sentence = sentences[seed % len(sentences)]
        is_true = rng.random() > 0.4
        concept = concepts[seed % len(concepts)] if concepts else "the topic"
        if is_true:
            question_text = f'True or False: According to your sources, "{sentence[:120].strip()}"'
            correct = "True"
        else:
            flipped = self._flip_statement(sentence, concept)
            question_text = f'True or False: According to your sources, "{flipped[:120].strip()}"'
            correct = "False"
        return QuizQuestion(
            id=self.store.next_id("q"),
            type="true_false",
            question_text=question_text,
            correct_answer=correct,
            points=1,
            options=["True", "False"],
        )

    def _make_short_answer(self, concepts: list[str], chunks: list, seed: int, guides: list) -> QuizQuestion:
        concept = concepts[seed % len(concepts)]
        s_guide = None
        for guide in guides:
            if concept.lower() in [c.lower() for c in guide.key_concepts]:
                s_guide = guide
                break
        question_text = f"Define or explain '{concept}' based on your uploaded sources."
        correct = concept
        if s_guide:
            correct = s_guide.summary[:200]
        return QuizQuestion(
            id=self.store.next_id("q"),
            type="short_answer",
            question_text=question_text,
            correct_answer=correct,
            points=3,
        )

    def _flip_statement(self, statement: str, concept: str) -> str:
        lowered = statement.lower()
        negation_words = ["is", "are", "was", "were", "has", "have", "does", "do", "can", "will"]
        for word in negation_words:
            pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
            if pattern.search(lowered):
                negated = re.sub(rf"\b{word}\b", f"{word} not", statement, count=1, flags=re.IGNORECASE)
                if negated != statement:
                    return negated[:200]
        return f"The opposite of '{concept}' is not supported by the sources."

    def _verify_question_key(self, question: QuizQuestion) -> tuple[bool, str]:
        if not question.correct_answer.strip():
            return False, "missing_answer"
        if question.type == "mcq":
            if not question.options or question.correct_answer not in question.options:
                return False, "mcq_answer_not_in_options"
            return True, "mcq_option_check"
        if question.type == "true_false":
            return question.correct_answer in {"True", "False"}, "boolean_key_check"
        if question.type == "short_answer":
            if question.citations:
                return True, "source_citation_check"
            return True, "source_guide_summary_check"
        return False, "unsupported_question_type"


def asdict_safe(obj):
    if obj is None:
        return None
    from dataclasses import asdict
    return asdict(obj)
