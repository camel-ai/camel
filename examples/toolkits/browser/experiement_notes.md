Task: Search for 1-bedroom apartments in New York in Upper East Side or Upper West Side or Murray Hill under $3,500 with washer/dryer.

1. token limit problem
2026-02-05 22:54:20.933 | INFO     | navi_bench.apartments.apartments_url_match:update:67 - ApartmentsUrlMatch.update did not find match: https://www.apartments.com/
2026-02-05 22:54:29.965 | INFO     | navi_bench.apartments.apartments_url_match:update:67 - ApartmentsUrlMatch.update did not find match: https://www.apartments.com/
2026-02-05 22:54:41.058 | INFO     | navi_bench.apartments.apartments_url_match:update:67 - ApartmentsUrlMatch.update did not find match: https://www.apartments.com/new-york-ny/
2026-02-05 22:55:02.648 | INFO     | navi_bench.apartments.apartments_url_match:update:67 - ApartmentsUrlMatch.update did not find match: https://www.apartments.com/new-york-ny/
2026-02-05 22:55:11.863 | INFO     | navi_bench.apartments.apartments_url_match:update:67 - ApartmentsUrlMatch.update did not find match: https://www.apartments.com/new-york-ny/
2026-02-05 22:55:11,895 - camel.camel.agents.chat_agent - WARNING - Token count (202141) exceed threshold (200000). Triggering summarization.
2026-02-05 22:55:32.598 | INFO     | navi_bench.apartments.apartments_url_match:update:67 - ApartmentsUrlMatch.update did not find match: https://www.apartments.com/new-york-ny/
2026-02-05 22:55:40.587 | INFO     | navi_bench.apartments.apartments_url_match:update:67 - ApartmentsUrlMatch.update did not find match: https://www.apartments.com/new-york-ny/?n=upper-east-side_new-york_ny
2026-02-05 22:56:01.138 | INFO     | navi_bench.apartments.apartments_url_match:update:67 - ApartmentsUrlMatch.update did not find match: https://www.apartments.com/new-york-ny/?n=upper-east-side_new-york_ny
2026-02-05 22:56:10.014 | INFO     | navi_bench.apartments.apartments_url_match:update:67 - ApartmentsUrlMatch.update did not find match: https://www.apartments.com/new-york-ny/?n=upper-east-side_new-york_ny
2026-02-05 22:56:10,056 - camel.camel.agents.chat_agent - WARNING - Token count (213509) exceed threshold (200220). Triggering summarization.

2. Some policy error
    "reasoning": "Attempt crashed: BadRequestError: Error code: 400 - {'error': {'message': \"The response was filtered due to the prompt triggering Azure OpenAI's content management policy. Please modify your prompt and retry. To learn more about our content filtering policies please read our documentation: https://go.microsoft.com/fwlink/?linkid=2198766\", 'type': None, 'param': 'prompt', 'code': 'content_filter', 'status': 400, 'innererror': {'code': 'ResponsibleAIPolicyViolation', 'content_filter_result': {'hate': {'filtered': False, 'severity': 'safe'}, 'jailbreak': {'filtered': False, 'detected': False}, 'self_harm': {'filtered': True, 'severity': 'medium'}, 'sexual': {'filtered': False, 'severity': 'safe'}, 'violence': {'filtered': False, 'severity': 'safe'}}}}}",

3. Problem to get the correct url match for evaluation.