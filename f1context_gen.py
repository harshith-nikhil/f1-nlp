#!/usr/bin/env python3
import json
import argparse

from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain

# ←–– Set your OpenAI API key here:
api_key = "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"

def parse_race_and_year(instruction: str):
    """
    Expecting instructions of the form:
      "Summarize the race results of <Race Name> <Year>"
    """
    prefix = "Summarize the race results of "
    if instruction.startswith(prefix):
        tail = instruction[len(prefix):].strip()
        parts = tail.rsplit(" ", 1)
        if len(parts) == 2:
            race, year = parts
            return race, year
    # Fallback
    return instruction, ""

def main():
    parser = argparse.ArgumentParser(
        description="Enhance each JSONL record of F1 results by filling in the 'response' field with a GPT-4o summary."
    )
    parser.add_argument(
        "-i", "--input", required=True,
        help="Path to input JSONL file (one record per line)"
    )
    parser.add_argument(
        "-o", "--output", required=True,
        help="Path to write output JSONL with populated responses"
    )
    args = parser.parse_args()

    # 1) Define our PromptTemplate
    template = """
You are a Formula 1 commentator writing for a high-end motorsport magazine.
Race: **{race} Grand Prix {year}**

Input data (JSON array of driver results):
{results_json}

Produce a comprehensive race report that includes:
1. **Race overview**
   – Who started on pole, who won, and by what margin (if known).
   – Any key early incidents or safety-car periods.
2. **Podium recap**
   – Name, team, start vs finish for P1–P3.
3. **Top-10 highlights**
   – For positions 4–10, note any standout moves or strategies.
4. **Biggest gainers/losers**
   – Who jumped most places? Who fell back dramatically?
5. **Retirements & DNFs**
   – Which drivers retired, and any known causes.
6. **Championship impact**
   – How did today’s points shuffle the standings (briefly)?

Write in **3-4 paragraphs** and use **bullet lists** where helpful.
"""
    prompt = PromptTemplate(
        input_variables=["race", "year", "results_json"],
        template=template.strip()
    )

    # 2) Instantiate the LLMChain with your API key
    llm = ChatOpenAI(
        model_name="gpt-4o",
        temperature=0.0,
        openai_api_key=api_key
    )
    chain = LLMChain(llm=llm, prompt=prompt)

    # 3) Process the file line-by-line
    with open(args.input, "r") as infile, open(args.output, "w") as outfile:
        for idx, line in enumerate(infile, start=1):
            print(f"[{idx}] ⏳ Reading record...")
            record = json.loads(line)

            instr = record.get("instruction", "")
            race, year = parse_race_and_year(instr)
            context = record.get("context", [])
            results_json = json.dumps(context)

            print(f"[{idx}] 🏎️ Generating summary for {race} {year}...")
            try:
                summary = chain.run(
                    race=race,
                    year=year,
                    results_json=results_json
                ).strip()
            except Exception as e:
                print(f"[{idx}] ❌ Error: {e}")
                summary = f"Error generating summary: {e}"

            record["response"] = summary
            outfile.write(json.dumps(record) + "\n")
            print(f"[{idx}] ✅ Done.\n")

    print("🎉 All records processed. Output written to:", args.output)

if __name__ == "__main__":
    main()
