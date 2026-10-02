"""
ragas_eval.py - Metric Ragas 0.4 (API collections) cho từng ca

    faithfulness            Tỉ lệ nhận định trong câu trả lời được ngữ cảnh truy xuất ủng hộ (chống bịa).
    factual_correctness     F1 nhận định giữa câu trả lời và câu trả lời chuẩn.
    context_recall          Ngữ cảnh truy xuất có đủ để suy ra câu trả lời chuẩn không.
    context_precision       Ngữ cảnh liên quan có được xếp trên cùng không.
    tool_call_f1            F1 giữa lời gọi tool của agent và reference_tool_calls (không dùng LLM).
Cần: pip install -r eval/requirements-eval.txt và OPENAI_API_KEY. Model chấm: MODEL_JUDGE (mặc định gpt-4o-mini).
"""
import os


def make_metrics():
    from openai import AsyncOpenAI
    from ragas.llms import llm_factory
    from ragas.metrics.collections import (
        ContextPrecisionWithReference,
        ContextRecall,
        FactualCorrectness,
        Faithfulness,
        ToolCallF1,
    )

    llm = llm_factory(os.getenv("MODEL_JUDGE") or "gpt-4o-mini", client=AsyncOpenAI())
    return dict(faithfulness=Faithfulness(llm=llm), factual_correctness=FactualCorrectness(llm=llm, mode="f1"),
                context_recall=ContextRecall(llm=llm), context_precision=ContextPrecisionWithReference(llm=llm),
                tool_call_f1=ToolCallF1())


def tool_messages(question, calls):
    from ragas.messages import AIMessage, HumanMessage, ToolCall

    return [HumanMessage(content=question),
            AIMessage(content="", tool_calls=[ToolCall(name=c["name"], args=c.get("args", {})) for c in calls])]


async def ragas_case(m, case, pred):
    """Chỉ tính metric khi đủ dữ liệu đầu vào; thiếu thì để None (không tính vào trung bình)."""
    from ragas.messages import ToolCall

    q, resp, ctx, ref = case["question"], pred.get("response", ""), pred.get("retrieved_contexts") or [], case["expected_answer"]
    out = dict(id=case["id"])
    out["faithfulness"] = (await m["faithfulness"].ascore(user_input=q, response=resp, retrieved_contexts=ctx)).value \
        if ctx else None
    out["factual_correctness"] = (await m["factual_correctness"].ascore(response=resp, reference=ref)).value
    if case["reference_contexts"]:
        out["context_recall"] = (await m["context_recall"].ascore(user_input=q, retrieved_contexts=ctx or [""],
                                                                  reference=ref)).value
        out["context_precision"] = (await m["context_precision"].ascore(user_input=q, reference=ref,
                                                                        retrieved_contexts=ctx)).value if ctx else 0.0
    out["tool_call_f1"] = (await m["tool_call_f1"].ascore(
        user_input=tool_messages(q, pred.get("tool_calls", [])),
        reference_tool_calls=[ToolCall(name=c["name"], args=c["args"]) for c in case["reference_tool_calls"]])).value
    return out
