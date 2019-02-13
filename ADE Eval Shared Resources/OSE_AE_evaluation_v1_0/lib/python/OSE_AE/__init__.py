# Copyright (C) 2018 The MITRE Corporation. See the toplevel
# file LICENSE.txt for license terms.

import os, sys

_THISDIR = os.path.dirname(os.path.abspath(__file__))
_MUNKRES_PATH = os.path.join(os.path.dirname(_THISDIR), "third_party", "munkres-1.0.5.4")
if _MUNKRES_PATH not in sys.path:
    sys.path.insert(0, _MUNKRES_PATH)
del _THISDIR, _MUNKRES_PATH
