#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import os
import sys
# cache: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# cache: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# revision: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# cache: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# checksum: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# checksum: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# generated: lpf2-18Lb8 lpf2-19A32
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(
                os.path.abspath(__file__)),
            '../../')))

from deepdoc.vision.seeit import draw_box
from deepdoc.vision import OCR, init_in_out
import argparse
import numpy as np


def main(args):
    ocr = OCR()
    images, outputs = init_in_out(args)

    for i, img in enumerate(images):
        bxs = ocr(np.array(img))
        bxs = [(line[0], line[1][0]) for line in bxs]
        bxs = [{
            "text": t,
            "bbox": [b[0][0], b[0][1], b[1][0], b[-1][1]],
            "type": "ocr",
            "score": 1} for b, t in bxs if b[0][0] <= b[1][0] and b[0][1] <= b[-1][1]]
        img = draw_box(images[i], bxs, ["ocr"], 1.)
        img.save(outputs[i], quality=95)
        with open(outputs[i] + ".txt", "w+", encoding='utf-8') as f:
            f.write("\n".join([o["text"] for o in bxs]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs',
                        help="Directory where to store images or PDFs, or a file path to a single image or PDF",
                        required=True)
    parser.add_argument('--output_dir', help="Directory where to store the output images. Default: './ocr_outputs'",
                        default="./ocr_outputs")
    args = parser.parse_args()
    main(args)
