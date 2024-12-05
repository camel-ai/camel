# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
from camel.toolkits import MeshyToolkit

toolkit = MeshyToolkit()

# Example data for testing
prompt = "A figuring of Tin tin the cartoon character"
art_style = "realistic"
negative_prompt = "low quality, low resolution, low poly, ugly"

# 3D model generation
print("Starting 3D model generation...")
final_response = toolkit.generate_3d_model_complete(
    prompt=prompt, art_style=art_style, negative_prompt=negative_prompt
)
print("\nFinal Response:", final_response)
# ruff: noqa: E501
"""
==========================================================================
Starting 3D model generation...
Status after 0s: PENDING
Status after 11s: IN_PROGRESS
Status after 22s: IN_PROGRESS
Status after 32s: SUCCEEDED
Status after 0s: PENDING
Status after 11s: IN_PROGRESS
Status after 21s: IN_PROGRESS
Status after 32s: IN_PROGRESS
Status after 43s: IN_PROGRESS
Status after 53s: IN_PROGRESS
Status after 64s: IN_PROGRESS
Status after 74s: IN_PROGRESS
Status after 85s: IN_PROGRESS
Status after 95s: IN_PROGRESS
Status after 106s: IN_PROGRESS
Status after 117s: SUCCEEDED

Final Response: {'id': '01939144-7dea-73c7-af06-efa79c83243f', 'mode': 
'refine', 'name': '', 'seed': 1733308970, 'art_style': 'realistic', 
'texture_richness': 'high', 'prompt': 'A figuring of Tin tin the cartoon 
character', 'negative_prompt': 'low quality, low resolution, low poly, ugly', 
'status': 'SUCCEEDED', 'created_at': 1733309005313, 'progress': 100, 
'started_at': 1733309006267, 'finished_at': 1733309113474, 'task_error': None, 
'model_urls': {'glb': 'https://assets.meshy.ai/5e05026a-0e91-4073-83fe-0263b1b4d348/tasks/01939144-7dea-73c7-af06-efa79c83243f/output/model.glb?Expires=4886870400&Signature=TEbWpN8sFZOf1FKWBVxKNdT2Ltm1Ma6vHuUUpBh6rZaAzfTBQPKvV2i7RmD~wwaebbQSBvVVagF4j587tNKNwHPqkGtpBjBu2q43n4lWM6W--RxSqbOCvVZ54PiAzzlVjM9PzPz-MasrWQtYipm5qJ5tsWd7XoxB6Wv2tZMZEWsftdLxmXdp9SuoBcu5NM~MRnyvhEYPmwU9uCAKfh4FZ14mhfx6TeDpCprYh1ngnlkLzDXk5Mdw0HJ1zuYpnkCOUtth84p6Oq5aU0HtWtUVd2tLi53rqKn9QC0qxcH7QlPxxI1aoUtzqaMXXiqCGylzZuPTZILhdFWeAoiEtCOLZw__&Key-Pair-Id=KL5I0C8H7HX83', 'fbx': 'https://assets.meshy.ai/5e05026a-0e91-4073-83fe-0263b1b4d348/tasks/01939144-7dea-73c7-af06-efa79c83243f/output/model.fbx?Expires=4886870400&Signature=jGOPhF8FL1wa9mVbodNoq1jMVzi2gklWRrrl2qWAZvWAhadc4wgjmgTweBKsNiO~KMTGzCiey7iqSIGm6dDEYAMv72HExpIO7I8HwAVPp4KwhzORzwr6OcEoY9-7fFR9yEg~WqnWewmdkrcnUVHHx2Z9imkDkIhISn1IOERkum48mTemlyejb87CXGV14uX3hxIVKle4at6S8tMUfpXhCdZ3aIxmgt9Dpsobol92XtQbpC-JhJSOgMNBWtAH3OUXAgECsYrRRZND9gcZZkUZlXHHZt439JsU8MPoXZd4RQ0OGn~vb6W51rvQ904ErsYZf47dLYNswaxb6Se3oKm~zw__&Key-Pair-Id=KL5I0C8H7HX83', 'usdz': 'https://assets.meshy.ai/5e05026a-0e91-4073-83fe-0263b1b4d348/tasks/01939144-7dea-73c7-af06-efa79c83243f/output/model.usdz?Expires=4886870400&Signature=ICOOIH6EDVdy9LYCk-azYqBWtl6t9v2xZpRk8C8kQKa38jUXdukjoLLN469VP5a7rdIKinLA~I5-hMr-kd-MEmwJzE3JKw2ojNimYPa5Uvnr3R~4S~2fQgCPWfn2xVkt6Cvfx~Qj8~ZNVxMj0jvnKkIySRHYaqvCxMfASHCB7Kz9LN3lBWuT709pEnQ6mtwLJWybLlIJkMFOVoapw~epIgWBtJjhMNwPCzXswUddKSdirOHIm8JRoN3~Ha99oxo4nSN5tyf3u2fWLxGOTeAyp7Hcq97gMkdqjuNc14k2n7fPULgbSCkHepLIG8GQrNLMfA6hkphkIj0LdjC6AQ7pvg__&Key-Pair-Id=KL5I0C8H7HX83', 'obj': 'https://assets.meshy.ai/5e05026a-0e91-4073-83fe-0263b1b4d348/tasks/01939144-7dea-73c7-af06-efa79c83243f/output/model.obj?Expires=4886870400&Signature=a53mEQASL7jRU8Xz5WhN-~d3~74BlBlqDMufryX-j1~jXTgbMEEhY2dC5R7dHHHJbJ4ns9GQ8cbjxcCImVvjkiLvPYZ-lraLaqMnbG~hatsZNv6wDZxTson8jsiqTSHaLnamp83zycLotM~zrUW0DIHGoFWvf9DPTKqy4Z0ZAOxOsA9qfAmJI6k2CVHLu0hMRLAjm3f8KA4j90kJBBVuYvABZi27hP-aURhD09zoAMp~AsrXSKxFjd5wcYqKko78qch2K2H5NaAUGhsKbuNmBMFaxc0C5dKgSlKufWmib86vUOe1dYLQyqGTS85u5dVQSwFrDY5gyugGJ4TH-aVQVw__&Key-Pair-Id=KL5I0C8H7HX83', 'mtl': 'https://assets.meshy.ai/5e05026a-0e91-4073-83fe-0263b1b4d348/tasks/01939144-7dea-73c7-af06-efa79c83243f/output/model.mtl?Expires=4886870400&Signature=FnY3cNMqEymvBw~33riU~HkVIifWKEUh0ndV90VaWMnKczU~Wqng7AYTqwywr6PNQDuFL~iQFw-y6qvklsV9I0aTg8OoYQ3dfCaRqydwUbN80aonk~fwpAJUwBxqbhhN4n9T~7WTX-pyo0w5vQ09wte4G-4yAIUEM7qlOwZohdfK2a~EIhnq9WiV92TuGtm0c4x5n6png9ZjX5pHnp~a77UCBJlIQ1teN5Rb3I9HFh4sbUGdcXUas7B9EIq4YiabjO9vf5FGwicb2XQ-YxJFJJdEJwbBp6l6iZCbSk-WijmIWmyD~8A~jhTNwlG9UHR5qTsnprntgoRyLdTRSXvDzg__&Key-Pair-Id=KL5I0C8H7HX83'}, 
'thumbnail_url': 'https://assets.meshy.ai/5e05026a-0e91-4073-83fe-0263b1b4d348/tasks/01939144-7dea-73c7-af06-efa79c83243f/output/preview.png?Expires=4886870400&Signature=B16evi199mig4RTFq0FVPrHGkpjpPudRpLfpcY2FxJIkIFYg42-v8BfsL3eWAM-XDlDqahPSXtqqm6emVkSu550iPqo2yy-URoDifiIl5petEy~42nHtc1-dZB1HcEvtcyycHOjmk1y8zQfZBgQ8cjGq0Ds19xSdOXIo7-~QDPWhUGUTreJvBNg17GitgvcfYbGj2g6gibYJWjwatM7A6yHhq3d53N8eDcmO5L6dBH3VwUFTxDWBQXwUT7aXkS7dsQ7Wz5CkIbbH~T-4Pn5KpdJy1Kf1Lrh1YpOUN4T7JI8Ot5urYKYRj4cZ96xpDD9gicPGvgrRaicFyb1sSwW2ow__&Key-Pair-Id=KL5I0C8H7HX83', 
'video_url': 'https://assets.meshy.ai/5e05026a-0e91-4073-83fe-0263b1b4d348/tasks/01939144-7dea-73c7-af06-efa79c83243f/output/output.mp4?Expires=4886870400&Signature=r8t11N9~XGzNfuW3KowxarSpr7hC8eQb0kzkKADOz3hdTA9vAqBdv5AVdMGDlMmH9IP4R60UCnVNT6scA1EeN3FZLXaHaWbsxHDuc4XdUk7DE7AbwUKSbl~YdUSu5-RkNu6vaMHTiB55XubUJhv9ReB25a6Ifee0rf1ulGs-amFSMlL~eNPq6HTUI6NGAqi1p~VeFzE53JV5sWvU2JYnbGe8kzruC705z1LiCU-9isWzJGuOIy~RpiVfYzSmgh4xeILaYKpxR2ZM2uVtbi6snl~aYsqiKMIIMxMg-aZDWn-f5voiWaCL1OUV5fxbI82ZRJNd5DSlVjI~umqZZIl-iw__&Key-Pair-Id=KL5I0C8H7HX83', 
'texture_urls': [{'base_color': 'https://assets.meshy.ai/5e05026a-0e91-4073-83fe-0263b1b4d348/tasks/01939144-7dea-73c7-af06-efa79c83243f/output/texture_0.png?Expires=4886870400&Signature=Q8SGRrnE00-mGHCAcIOUUAig~YtTJqVx1n2IqFFbXBNUPvf~hsTYzcKgC2wQjF25tj0D6yQ8BiIktN9WjsKu0SnbeED~ofHIA0quheMjwHL~hfdj63LGWkMumVEjE2ZVwDv-DdlROF3ayw5hQxzlRbcHwXLq0n2xMHmj-WetyiYBKCcJbXbZMOAtlo8e40d21CGMnjImduCvdwhpqwNKUx4MwHeM2W0GW4OC94AoSF8AccHJeQPD2gdu7JHoTuZFjcqS-9YCjmHT7Y5Xg7rmeNYz40O21sYci0b54NvBDzX-6HvydjqtY-ofudppaxlC77Zd~FaVcCz5rH2J43cdLg__&Key-Pair-Id=KL5I0C8H7HX83'}]}
(camel-ai-py3.12) 
==========================================================================
"""
