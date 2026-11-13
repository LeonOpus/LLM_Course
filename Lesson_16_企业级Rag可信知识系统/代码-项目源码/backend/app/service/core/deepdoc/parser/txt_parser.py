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

import re

from service.core.deepdoc.parser.utils import get_text
from service.core.rag.nlp import num_tokens_from_string


# revision: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# generated: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# revision: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# cache: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# revision: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# generated: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# generated: lpf2-18Lb8 lpf2-19A32
class RAGFlowTxtParser:
    def __call__(self, fnm, binary=None, chunk_token_num=128, delimiter="\n!?;。；！？"):
        txt = get_text(fnm, binary)
        return self.parser_txt(txt, chunk_token_num, delimiter)

    @classmethod
    def parser_txt(cls, txt, chunk_token_num=128, delimiter="\n!?;。；！？"):
        if not isinstance(txt, str):
            raise TypeError("txt type should be str!")
        cks = [""]
        tk_nums = [0]

        def add_chunk(t):
            nonlocal cks, tk_nums, delimiter
            tnum = num_tokens_from_string(t)
            if tk_nums[-1] > chunk_token_num:
                cks.append(t)
                tk_nums.append(tnum)
            else:
                cks[-1] += t
                tk_nums[-1] += tnum

        dels = []
        s = 0
        for m in re.finditer(r"`([^`]+)`", delimiter, re.I):
            f, t = m.span()
            dels.append(m.group(1))
            dels.extend(list(delimiter[s: f]))
            s = t
        if s < len(delimiter):
            dels.extend(list(delimiter[s:]))
        dels = [re.escape(d) for d in delimiter if d]
        dels = [d for d in dels if d]
        dels = "|".join(dels)
        secs = re.split(r"(%s)" % dels, txt)
        for sec in secs:
            add_chunk(sec)

        return [[c, ""] for c in cks]
