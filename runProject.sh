#!/usr/bin/bash

#May want to add the install lines in here if time, such as the rhino install or the text2digits install
pip3 install text2digits
pip3 install pvrhino

python3 newProjectAttemptFromDemoScript.py --access_key API_key_here --context_path BibleVerseRecognizerAlphaModel.rhn
