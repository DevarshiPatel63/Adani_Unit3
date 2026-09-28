"""
Theory 12 — Demo 1: SIMPLE DELEGATION (NOT A2A YET)

Two Python functions in the same file. One pretends to be a "main agent",
the other a "research specialist." The main agent DELEGATES to the specialist
instead of doing the work itself.

Why show this first?
    Delegation is the *idea*. A2A is the *protocol* for doing delegation
    across a network. Getting the idea straight makes the protocol
    obvious later.

Important: this is NOT A2A.
    - Both functions live in the same Python process.
    - Nothing goes over the network.
    - No Agent Card, no server, no protocol.

Run:
    python demo1_delegation.py
"""


def research_agent(question: str) -> str:
    # A pretend specialist. In a real system this would call an LLM,
    # hit a database, do web search, etc. For now just prove we called it.
    return f"[research finding for: {question!r}]"


def main_agent(question: str) -> str:
    # The main agent does NOT answer the question itself.
    # It DELEGATES to the specialist and wraps the answer.
    print("main_agent  → delegating to research_agent")
    finding = research_agent(question)
    print(f"main_agent  ← got finding: {finding}")
    return f"Final answer, built using: {finding}"


if __name__ == "__main__":
    question = input("Ask a question: ")
    print()
    answer = main_agent(question)
    print(f"\nANSWER: {answer}")
