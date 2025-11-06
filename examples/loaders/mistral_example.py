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
    file_path="https://arxiv.org/pdf/2201.04234", pages=[5]
)
print(url_ocr_response)
"""
============================================================================
pages=[OCRPageObject(index=5, markdown='![img-0.jpeg](img-0.jpeg)\n\nFigure 2: 
Scatter plot of predicted accuracy versus (true) OOD accuracy. Each point 
denotes a different OOD dataset, all evaluated with the same DenseNet121 
model. We only plot the best three methods. With ATC (ours), we refer to 
ATC-NE. We observe that ATC significantly outperforms other methods and with 
ATC, we recover the desired line $y=x$ with a robust linear fit. Aggregated 
estimation error in Table 1 and plots for other datasets and architectures in 
App. H.\nof the target accuracy with various methods given access to only 
unlabeled data from the target. Unless noted otherwise, all models are trained 
only on samples from the source distribution with the main exception of 
pre-training on a different distribution. We use labeled examples from the 
target distribution to only obtain true error estimates.\n\nDatasets. First, 
we consider synthetic shifts induced due to different visual corruptions (e.
g., shot noise, motion blur etc.) under ImageNet-C (Hendrycks \\& Dietterich, 
2019). Next, we consider natural shifts due to differences in the data 
collection process of ImageNet (Russakovsky et al., 2015), e.g, ImageNetv2 
(Recht et al., 2019). We also consider images with artistic renditions of 
object classes, i.e., ImageNet-R (Hendrycks et al., 2021) and ImageNet-Sketch 
(Wang et al., 2019). Note that renditions dataset only contains a subset 200 
classes from ImageNet. To include renditions dataset in our testbed, we 
include results on ImageNet restricted to these 200 classes (which we call 
ImageNet-200) along with full ImageNet.\n\nSecond, we consider BREEDS 
(Santurkar et al., 2020) to assess robustness to subpopulation shifts, in 
particular, to understand how accuracy estimation methods behave when novel 
subpopulations not observed during training are introduced. BREEDS leverages 
class hierarchy in ImageNet to create 4 datasets ENTITY-13, ENTITY-30, 
LIVING-17, NON-LIVING-26. We focus on natural and synthetic shifts as in 
ImageNet on same and different subpopulations in BREEDs. Third, from WILDS 
(Koh et al., 2021) benchmark, we consider FMoW-WILDS (Christie et al., 2018), 
RxRx1-WILDS (Taylor et al., 2019), Amazon-WILDS (Ni et al., 2019), 
CivilComments-WILDS (Borkan et al., 2019) to consider distribution shifts 
faced in the wild.\n\nFinally, similar to ImageNet, we consider (i) synthetic 
shifts (CIFAR-10-C) due to common corruptions; and (ii) natural shift (i.e., 
CIFARv2 (Recht et al., 2018)) on CIFAR-10 (Krizhevsky \\& Hinton, 2009). On 
CIFAR-100, we just have synthetic shifts due to common corruptions. For 
completeness, we also consider natural shifts on MNIST (LeCun et al., 1998) as 
in the prior work (Deng \\& Zheng, 2021). We use three real shifted datasets, 
i.e., USPS (Hull, 1994), SVHN (Netzer et al., 2011) and QMNIST (Yadav \\& 
Bottou, 2019). We give a detailed overview of our setup in App. F.
\n\nArchitectures and Evaluation. For ImageNet, BREEDS, CIFAR, FMoW-WILDS, 
RxRx1-WILDS datasets, we use DenseNet121 (Huang et al., 2017) and ResNet50 (He 
et al., 2016) architectures. For Amazon-WILDS and CivilComments-WILDS, we 
fine-tune a DistilBERT-base-uncased (Sanh et al., 2019) model. For MNIST, we 
train a fully connected multilayer perceptron. We use standard training with 
benchmarked hyperparameters. To compare methods, we report average absolute 
difference between the true accuracy on the target data and the estimated 
accuracy on the same unlabeled examples. We refer to this metric as Mean 
Absolute estimation Error (MAE). Along with MAE, we also show scatter plots to 
visualize performance at individual target sets. Refer to App. G for 
additional details on the setup.\n\nMethods With ATC-NE, we denote ATC with 
negative entropy score function and with ATC-MC, we denote ATC with maximum 
confidence score function. For all methods, we implement post-hoc calibration 
on validation source data with Temperature Scaling (TS; Guo et al. (2017)). 
Below we briefly discuss baselines methods compared in our work and relegate 
details to App. E.', images=[OCRImageObject(id='img-0.jpeg', top_left_x=294, 
top_left_y=180, bottom_right_x=1387, bottom_right_y=558, image_base64=None, 
image_annotation=None)], dimensions=OCRPageDimensions(dpi=200, height=2200, 
width=1700))] model='mistral-ocr-2505-completion' usage_info=OCRUsageInfo
(pages_processed=1, doc_size_bytes=3002783) document_annotation=None
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
