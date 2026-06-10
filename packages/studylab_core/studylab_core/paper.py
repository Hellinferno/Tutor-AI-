from __future__ import annotations

from .models import AnswerKey, PaperSection, QuestionPaper
from .quiz import QuizEngine
from .rag import RagEngine
from .store import InMemoryStudyLabStore


class PaperEngine:
    def __init__(self, store: InMemoryStudyLabStore, rag: RagEngine, quiz: QuizEngine) -> None:
        self.store = store
        self.rag = rag
        self.quiz = quiz

    def generate_paper(
        self,
        notebook_id: str,
        sections: list[dict] | None = None,
        duration_minutes: int = 60,
        topic: str | None = None,
    ) -> QuestionPaper:
        self.store.require_notebook(notebook_id)
        guides = self.store.notebook_guides(notebook_id)

        if not guides and not topic:
            raise ValueError("Cannot generate question paper: notebook has no sources or guides.")

        if sections is None:
            sections = [
                {"title": "Multiple Choice", "num_questions": 3, "type": "mcq"},
                {"title": "True or False", "num_questions": 2, "type": "true_false"},
                {"title": "Short Answer", "num_questions": 2, "type": "short_answer"},
            ]

        total_marks = 0
        paper_sections: list[PaperSection] = []
        for idx, section_def in enumerate(sections):
            q_type = section_def.get("type", "mcq")
            nq = section_def.get("num_questions", 2)
            quiz = self.quiz.generate_quiz(
                notebook_id=notebook_id,
                num_questions=nq,
                question_types=[q_type],
                topic=topic or section_def.get("title"),
            )
            section_marks = sum(q.points for q in quiz.questions)
            total_marks += section_marks
            instruction = f"Answer all {nq} questions. Each question carries marks as shown."
            paper_sections.append(PaperSection(
                title=section_def["title"],
                instructions=section_def.get("instructions", instruction),
                questions=quiz.questions,
            ))

        notebook = self.store.require_notebook(notebook_id)
        paper = QuestionPaper(
            id=self.store.next_id("paper"),
            notebook_id=notebook_id,
            title=f"{notebook.title} - Question Paper",
            sections=paper_sections,
            total_marks=total_marks,
            duration_minutes=duration_minutes,
        )
        return self.store.add_question_paper(paper)

    def generate_answer_key(self, paper_id: str) -> AnswerKey:
        paper = self.store.require_question_paper(paper_id)
        answers = []
        for section in paper.sections:
            for q in section.questions:
                verified = bool(q.correct_answer.strip())
                method = "paper_section_key_check" if verified else "missing_answer"
                answers.append({
                    "section_title": section.title,
                    "question_id": q.id,
                    "question_text": q.question_text,
                    "correct_answer": q.correct_answer,
                    "type": q.type,
                    "options": q.options,
                    "points": q.points,
                    "verified": verified,
                    "verification_method": method,
                })
        key = AnswerKey(
            id=self.store.next_id("answer_key"),
            source_id=paper_id,
            source_type="paper",
            answers=answers,
            verified=all(answer["verified"] for answer in answers),
            verification_method="paper_answer_key_check",
        )
        return self.store.add_answer_key(key)

    def get_paper(self, paper_id: str, include_answers: bool = False) -> QuestionPaper:
        paper = self.store.require_question_paper(paper_id)
        if not include_answers:
            hidden_sections = []
            for section in paper.sections:
                hidden_questions = []
                for q in section.questions:
                    from .models import QuizQuestion
                    hidden_questions.append(QuizQuestion(
                        id=q.id,
                        type=q.type,
                        question_text=q.question_text,
                        correct_answer="",
                        points=q.points,
                        difficulty=q.difficulty,
                        options=q.options,
                        citations=None,
                    ))
                hidden_sections.append(PaperSection(
                    title=section.title,
                    instructions=section.instructions,
                    questions=hidden_questions,
                ))
            return QuestionPaper(
                id=paper.id,
                notebook_id=paper.notebook_id,
                title=paper.title,
                sections=hidden_sections,
                total_marks=paper.total_marks,
                duration_minutes=paper.duration_minutes,
            )
        return paper
