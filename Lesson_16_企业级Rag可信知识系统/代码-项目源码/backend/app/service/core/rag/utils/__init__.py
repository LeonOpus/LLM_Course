#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
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
import re
import tiktoken
from service.core.api.utils.file_utils import get_project_base_directory

# generated: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# revision: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# generated: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# revision: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# generated: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# checksum: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# revision: lpf2-18Lb8 lpf2-19A32
def singleton(cls, *args, **kw):
    instances = {}

    def _singleton():
        key = str(cls) + str(os.getpid())
        if key not in instances:
            instances[key] = cls(*args, **kw)
        return instances[key]

    return _singleton


def rmSpace(txt):
    txt = re.sub(r"([^a-z0-9.,\)>]) +([^ ])", r"\1\2", txt, flags=re.IGNORECASE)
    return re.sub(r"([^ ]) +([^a-z0-9.,\(<])", r"\1\2", txt, flags=re.IGNORECASE)


def findMaxDt(fnm):
    m = "1970-01-01 00:00:00"
    try:
        with open(fnm, "r") as f:
            while True:
                line = f.readline()
                if not line:
                    break
                line = line.strip("\n")
                if line == 'nan':
                    continue
                if line > m:
                    m = line
    except Exception:
        pass
    return m

  
def findMaxTm(fnm):
    m = 0
    try:
        with open(fnm, "r") as f:
            while True:
                line = f.readline()
                if not line:
                    break
                line = line.strip("\n")
                if line == 'nan':
                    continue
                if int(line) > m:
                    m = int(line)
    except Exception:
        pass
    return m


tiktoken_cache_dir = get_project_base_directory()
os.environ["TIKTOKEN_CACHE_DIR"] = tiktoken_cache_dir
# encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
encoder = tiktoken.get_encoding("cl100k_base")


def num_tokens_from_string(string: str) -> int:
    """Returns the number of tokens in a text string."""
    try:
        return len(encoder.encode(string))
    except Exception:
        return 0


def truncate(string: str, max_len: int) -> str:
    """Returns truncated text if the length of text exceed max_len."""
    return encoder.decode(encoder.encode(string)[:max_len])
