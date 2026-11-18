"""The only platform package that calls the research engine.

Eligibility stays in the research pipeline. These modules load inputs, call
``pipeline.run``, and read stored market data. They do not score gates.
"""
