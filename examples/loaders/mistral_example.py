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

import os
import tempfile

from camel.loaders import MistralReader

mistral_reader = MistralReader()
url_ocr_response = mistral_reader.extract_text(
    file_path="https://arxiv.org/pdf/2201.04234", pages=[0]
)
print(url_ocr_response)
"""
============================================================================
pages=[OCRPageObject(index=0, markdown="# Leveraging Unlabeled Data to Predict 
Out-of-Distribution Performance \n\nSaurabh Garg*<br>Carnegie Mellon 
University<br>sgarg2@andrew.cmu.edu Sivaraman Balakrishnan<br>Carnegie Mellon 
University<br>sbalakri@andrew.cmu.edu Zachary C. Lipton<br>Carnegie Mellon 
University<br>zlipton@andrew.cmu.edu\n\n## Behnam Neyshabur\n\nGoogle 
Research, Blueshift team neyshabur@google.com\n\n## Hanie Sedghi\n\nGoogle 
Research, Brain team hsedghi@google.com\n\n## ABSTRACT\n\nReal-world machine 
learning deployments are characterized by mismatches between the source 
(training) and target (test) distributions that may cause performance drops. 
In this work, we investigate methods for predicting the target domain accuracy 
using only labeled source data and unlabeled target data. We propose Average 
Thresholded Confidence (ATC), a practical method that learns a threshold on 
the model's confidence, predicting accuracy as the fraction of unlabeled 
examples for which model confidence exceeds that threshold. ATC outperforms 
previous methods across several model architectures, types of distribution 
shifts (e.g., due to synthetic corruptions, dataset reproduction, or novel 
subpopulations), and datasets (WILDS, ImageNet, BREEDS, CIFAR, and MNIST). In 
our experiments, ATC estimates target performance $2-4 \\times$ more 
accurately than prior methods. We also explore the theoretical foundations of 
the problem, proving that, in general, identifying the accuracy is just as 
hard as identifying the optimal predictor and thus, the efficacy of any method 
rests upon (perhaps unstated) assumptions on the nature of the shift. Finally, 
analyzing our method on some toy distributions, we provide insights concerning 
when it works ${ }^{1}$.\n\n## 1 INTRODUCTION\n\nMachine learning models 
deployed in the real world typically encounter examples from previously unseen 
distributions. While the IID assumption enables us to evaluate models using 
held-out data from the source distribution (from which training data is 
sampled), this estimate is no longer valid in presence of a distribution 
shift. Moreover, under such shifts, model accuracy tends to degrade (Szegedy 
et al., 2014; Recht et al., 2019; Koh et al., 2021). Commonly, the only data 
available to the practitioner are a labeled training set (source) and 
unlabeled deployment-time data which makes the problem more difficult. In this 
setting, detecting shifts in the distribution of covariates is known to be 
possible (but difficult) in theory (Ramdas et al., 2015), and in practice 
(Rabanser et al., 2018). However, producing an optimal predictor using only 
labeled source and unlabeled target data is well-known to be impossible absent 
further assumptions (Ben-David et al., 2010; Lipton et al., 2018).\n\nTwo 
vital questions that remain are: (i) the precise conditions under which we can 
estimate a classifier's target-domain accuracy; and (ii) which methods are 
most practically useful. To begin, the straightforward way to assess the 
performance of a model under distribution shift would be to collect labeled 
(target domain) examples and then to evaluate the model on that data. However, 
collecting fresh labeled data from the target distribution is prohibitively 
expensive and time-consuming, especially if the target distribution is 
non-stationary. Hence, instead of using labeled data, we aim to use unlabeled 
data from the target distribution, that is comparatively abundant, to predict 
model performance. Note that in this work, our focus is not to improve 
performance on the target but, rather, to estimate the accuracy on the target 
for a given classifier.\n\n[^0]\n[^0]:    * Work done in part while Saurabh 
Garg was interning at Google\n    ${ }^{1}$ Code is available at https://
github.com/saurabhgarg1996/ATC_code.", images=[], dimensions=OCRPageDimensions
(dpi=200, height=2200, width=1700))] model='mistral-ocr-2505-completion' 
usage_info=OCRUsageInfo(pages_processed=1, doc_size_bytes=3002783) 
document_annotation=None
============================================================================
"""


image_ocr_response = mistral_reader.extract_text(
    file_path="https://raw.githubusercontent.com/mistralai/cookbook/refs/heads/main/mistral/ocr/receipt.png",
    is_image=True,
)
print(image_ocr_response)
"""
============================================================================
pages=[OCRPageObject(index=0, markdown='PLACE FACE UP ON DASH\nCITY OF PALO 
ALTO\nNOT VALID FOR\nONSTREET PARKING\n\nExpiration Date/Time\n11:59 PM\nAUG 
19, 2024\n\nPurchase Date/Time: 01:34pm Aug 19, 2024\nTotal Due: $15.00\nTotal 
Paid: $15.00\nTicket #: 00005883\nS/N #: 520117260957\nSetting: Permit 
Machines\nMach Name: Civic Center\n\n#****-1224, Visa\nDISPLAY FACE UP ON 
DASH\n\nPERMIT EXPIRES\nAT MIDNIGHT', images=[], dimensions=OCRPageDimensions
(dpi=200, height=3210, width=1806))] model='mistral-ocr-2505-completion' 
usage_info=OCRUsageInfo(pages_processed=1, doc_size_bytes=3110191) 
document_annotation=None
============================================================================
"""


mock_files = {
    "report.pdf": "%PDF-1.4\n%âãÏÓ\n1 0 obj\n<</Type/Catalog/Pages 2 0"
    " R>>\nendobj\n2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 "
    "0 obj\n<</Type/Page/MediaBox[0 0 595 842]/Resources<<>>/Contents 4 0 "
    "R/Parent 2 0 R>>\nendobj\n4 0 obj\n<</Length 150>>\nstream\nBT\n/F1 "
    "12 Tf\n50 750 Td\n(CAMEL AI Research Report) Tj\n0 -20 Td\n(This is "
    "a complex mock PDF document for testing OCR capabilities.) Tj\n0 -20 "
    "Td\n(It contains multiple lines of text and "
    "formatting.) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 "
    "65535 f\n0000000010 00000 n\n0000000056 00000 n\n0000000111 "
    "00000 n\n0000000212 00000 n\ntrailer\n<</Size 5/Root 1 "
    "0 R>>\nstartxref\n362\n%%EOF",
}

with tempfile.TemporaryDirectory() as temp_dir:
    file_paths = {}

    for filename, content in mock_files.items():
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, "w") as f:
            f.write(content)
        file_paths[filename] = file_path

    local_ocr_response = mistral_reader.extract_text(file_paths["report.pdf"])
    print(local_ocr_response)

"""
============================================================================
pages=[OCRPageObject(index=0, markdown='PLACE FACE UP ON DASH\nCITY OF PALO 
ALTO\nNOT VALID FOR\nONSTREET PARKING\n\nExpiration Date/Time\n11:59 PM\nAUG 
19, 2024\n\nPurchase Date/Time: 01:34pm Aug 19, 2024\nTotal Due: $15.00\nTotal 
Paid: $15.00\nTicket #: 00005883\nS/N #: 520117260957\nSetting: Permit 
Machines\nMach Name: Civic Center\n\n#****-1224, Visa\nDISPLAY FACE UP ON 
DASH\n\nPERMIT EXPIRES\nAT MIDNIGHT', images=[], dimensions=OCRPageDimensions
(dpi=200, height=3210, width=1806))] model='mistral-ocr-2505-completion' 
usage_info=OCRUsageInfo(pages_processed=1, doc_size_bytes=3110191) 
document_annotation=None
pages=[OCRPageObject(index=0, markdown='CAMEL AI Research Report\nThis is a 
complex mock PDF document for testing OCR capabilities.\nIt contains multiple 
lines of text and formatting.', images=[], dimensions=OCRPageDimensions
(dpi=200, height=2339, width=1653))] model='mistral-ocr-2505-completion' 
usage_info=OCRUsageInfo(pages_processed=1, doc_size_bytes=612) 
document_annotation=None
============================================================================
"""
