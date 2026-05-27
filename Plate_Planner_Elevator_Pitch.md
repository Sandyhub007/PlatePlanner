# Plate Planner — 4-Person Elevator Pitch

**Format:** 4 speakers, ~22 seconds each &nbsp;•&nbsp; **Total target: 1 min 30 sec**
**Approx. word count:** ~200 words at a relaxed conversational pace (≈140 wpm)

Each speaker's segment is sized so the team can hand off cleanly without rushing. Stage directions in *italics*.

---

## 🎤 Speaker 1 — Sandilya Chimalamarri  *(ML Lead — opens, frames the problem)*  &nbsp;~21 sec

> "Hi — we're the Plate Planner team.
>
> The average household spends three to five hours a week just deciding what to cook. Recipe apps surface dishes by keyword, but they rarely understand what's actually in your pantry — and almost never tell you what to swap when an ingredient is missing.
>
> **Plate Planner fixes exactly that.**"

*Delivery: warm, conversational. Land "three to five hours a week" — that's the hook. Pause briefly before the last line, then say it with conviction.*
*Hands off to:* &nbsp;**Sai Priyanka.**

---

## 🎤 Speaker 2 — Sai Priyanka Bonkuri  *(Graph Architect — the "how it knows")*  &nbsp;~20 sec

> "At the core is a **Neo4j property graph** — fifty thousand recipes, twelve thousand ingredients, connected by `HAS_INGREDIENT`, `SUBSTITUTES_WITH`, and `SIMILAR_TO` edges.
>
> Our substitution edges store the *cooking context*. So 'what can I use instead of butter in baking?' returns **margarine and shortening** — not random co-occurring ingredients."

*Delivery: technical but enthusiastic. Emphasise "cooking context" — that's the differentiator. Use the butter example as a concrete moment people can picture.*
*Hands off to:* &nbsp;**Pavan Charith.**

---

## 🎤 Speaker 3 — Pavan Charith Devarapalli  *(Backend — the "how it's fast")*  &nbsp;~22 sec

> "On top of the graph we run **MiniLM sentence embeddings and a FAISS index**, served behind a single FastAPI endpoint.
>
> Suggestions blend semantic similarity with ingredient overlap — sixty / forty in our hybrid score. End-to-end **p95 latency is seventy-eight milliseconds**, with a hundred-plus requests per second on commodity hardware."

*Delivery: confident, specific. Numbers carry this segment — let "seventy-eight milliseconds" land. Avoid mumbling acronyms; pronounce FAISS as "face."*
*Hands off to:* &nbsp;**Sai Dheeraj.**

---

## 🎤 Speaker 4 — Sai Dheeraj Gollu  *(Pipeline — the "it actually works" + close)*  &nbsp;~22 sec

> "Everything — Neo4j, FAISS, the React Native mobile client — is **fully containerized and runs on a laptop**.
>
> On a sixty-ingredient evaluation panel, our hybrid substitution lifts top-five coverage by **twenty-three percent** over direct-only baselines.
>
> **Plate Planner — turn what's already in your pantry into dinner.**
>
> Thank you."

*Delivery: bring the energy back up for the close. Hit "twenty-three percent" cleanly. The tagline is the last thing the audience hears — say it slowly and look at them. End with a confident smile.*

---

## ⏱️ Timing Cheat Sheet

| # | Speaker | Role | Beats | Duration |
|---|---------|------|-------|----------|
| 1 | **Sandilya** | ML Lead | Hook → Problem → Solution name | ~21 s |
| 2 | **Sai Priyanka** | Graph Architect | Graph schema → context-aware substitution | ~20 s |
| 3 | **Pavan Charith** | Backend Engineer | Embeddings + FAISS + hybrid score → latency | ~22 s |
| 4 | **Sai Dheeraj** | Pipeline Engineer | Stack → results → tagline → thank you | ~22 s |
| | | | **TOTAL** | **~1 min 25 s** |

Five-second buffer left for natural pauses and audience reaction.

---

## 🎯 The Four Things You Want the Audience to Remember

1. **Problem:** Pantry-aware cooking is genuinely hard. (3–5 hours / week)
2. **Trick:** Property graph + sentence embeddings, blended.
3. **Speed:** 78 ms p95, runs on a laptop.
4. **Win:** +23 % top-5 coverage on substitution vs. baselines.

---

## 🎬 Delivery Tips

- **Stand in a tight semicircle**, not a straight line — feels like a team, not a queue.
- **Eye contact passes with the words.** When you finish, look at the next speaker for half a second; they pick up immediately.
- **Pronounce acronyms naturally:** "FAISS" → *face*, "API" → *A-P-I*, "Neo4j" → *Neo-four-jay*.
- **Don't rehearse it word-for-word.** Memorize the 1–2 key phrases per slot (the bolded bits), and let the connective tissue stay conversational.
- **Practice the handoffs.** A clean handoff sounds rehearsed; a fumbled one breaks the spell.
- If asked a follow-up: **whoever owns that area takes it.** ML → Sandilya, Graph → Sai Priyanka, API → Pavan Charith, Pipeline & Demo → Sai Dheeraj.
