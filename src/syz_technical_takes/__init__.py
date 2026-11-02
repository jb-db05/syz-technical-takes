"""syz_technical_takes - the deterministic half of the technical-takes skill.

Pipeline: data (OHLC feed) -> indicators (synthesize the Bloomberg workbook,
including the decoded %DS/%DSS stochastic) -> analytics (the §7 verdict inputs)
-> render (the 3-page A4 PDF). The model authors only the verdict spec.
"""
__all__ = ["data", "indicators", "analytics", "benchmarks", "render", "cli"]
