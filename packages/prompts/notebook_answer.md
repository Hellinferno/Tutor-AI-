# Notebook Answer (Grounded)

Answer the student's question using ONLY the retrieved source chunks below. Every claim must
trace to a chunk. Cite each supporting chunk inline as `[source_title, chunk N]`.

Question: {{query}}

Retrieved chunks:
{{chunks}}

Rules:
- If the chunks do not contain enough support, respond exactly with an insufficient-support
  refusal and suggest uploading a more relevant source or asking a narrower question. Do NOT
  answer from general knowledge when grounding is requested.
- Never fabricate a citation. Only cite chunks that are actually present above.
- Prefer quoting or closely paraphrasing the source over summarizing loosely.
