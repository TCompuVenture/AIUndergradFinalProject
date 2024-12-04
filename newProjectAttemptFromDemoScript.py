# This file modified from source found here: https://github.com/Picovoice/rhino/tree/master/demo/python
#License provided as required in this Github repo

import argparse
import struct
import wave
from text2digits import text2digits
#import urllib.request
import json
import requests

import pvrhino
from pvrecorder import PvRecorder



def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--access_key',
        help='AccessKey obtained from Picovoice Console (https://console.picovoice.ai/)')

    parser.add_argument(
        '--context_path',
        help="Absolute path to context file.")

    parser.add_argument(
        '--library_path',
        help='Absolute path to dynamic library. Default: using the library provided by `pvrhino`')

    parser.add_argument(
        '--model_path',
        help='Absolute path to the file containing model parameters. Default: using the library provided by `pvrhino`')

    parser.add_argument(
        '--sensitivity',
        help="Inference sensitivity. It should be a number within [0, 1]. A higher sensitivity value results in "
             "fewer misses at the cost of (potentially) increasing the erroneous inference rate.",
        type=float,
        default=0.5)

    parser.add_argument(
        '--endpoint_duration_sec',
        help="Endpoint duration in seconds. An endpoint is a chunk of silence at the end of an utterance that marks "
             "the end of spoken command. It should be a positive number within [0.5, 5]. A lower endpoint duration "
             "reduces delay and improves responsiveness. A higher endpoint duration assures Rhino doesn't return "
             "inference preemptively in case the user pauses before finishing the request.",
        type=float,
        default=1.)

    parser.add_argument(
        '--require_endpoint',
        help="If set to `True`, Rhino requires an endpoint (a chunk of silence) after the spoken command. If set to "
             "`False`, Rhino tries to detect silence, but if it cannot, it still will provide inference regardless. "
             "Set to `False` only if operating in an environment with overlapping speech (e.g. people talking in the "
             "background).",
        default='True',
        choices=['True', 'False'])

    parser.add_argument('--audio_device_index', help='Index of input audio device.', type=int, default=-1)

    parser.add_argument('--output_path', help='Absolute path to recorded audio for debugging.', default=None)

    parser.add_argument('--show_audio_devices', action='store_true')

    args = parser.parse_args()

    if args.require_endpoint.lower() == 'false':
        require_endpoint = False
    else:
        require_endpoint = True

    if args.show_audio_devices:
        for i, device in enumerate(PvRecorder.get_available_devices()):
            print('Device %d: %s' % (i, device))
        return

    if not args.access_key or not args.context_path:
        print('--access_key and --context_path are required.')
        return

    try:
        rhino = pvrhino.create(
            access_key=args.access_key,
            library_path=args.library_path,
            model_path=args.model_path,
            context_path=args.context_path,
            sensitivity=args.sensitivity,
            endpoint_duration_sec=args.endpoint_duration_sec,
            require_endpoint=require_endpoint)
    except pvrhino.RhinoInvalidArgumentError as e:
        print("One or more arguments provided to Rhino is invalid: ", args)
        print(e)
        raise e
    except pvrhino.RhinoActivationError as e:
        print("AccessKey activation error")
        raise e
    except pvrhino.RhinoActivationLimitError as e:
        print("AccessKey '%s' has reached it's temporary device limit" % args.access_key)
        raise e
    except pvrhino.RhinoActivationRefusedError as e:
        print("AccessKey '%s' refused" % args.access_key)
        raise e
    except pvrhino.RhinoActivationThrottledError as e:
        print("AccessKey '%s' has been throttled" % args.access_key)
        raise e
    except pvrhino.RhinoError as e:
        print("Failed to initialize Rhino")
        raise e

    print('Rhino version: %s' % rhino.version)
   # print('Context info: %s' % rhino.context_info) #Comment this out to make it not display TOTAL context info on every startup!

    recorder = PvRecorder(
        frame_length=rhino.frame_length,
        device_index=args.audio_device_index)
    recorder.start()

    print('Using device: %s' % recorder.selected_device)
    print('Listening ... Press Ctrl+C to exit.\n')

    wav_file = None
    if args.output_path is not None:
        wav_file = wave.open(args.output_path, 'wb')
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(recorder.sample_rate)

    try:
        while True:
            pcm = recorder.read()

            if wav_file is not None:
                wav_file.writeframes(struct.pack("h" * len(pcm), *pcm))

            is_finalized = rhino.process(pcm)
            if is_finalized:
                inference = rhino.get_inference()
                if inference.is_understood:
                    thebook = ""
                    thechapter = 0
                    theverse = 0
                    t2d = text2digits.Text2Digits()
                    #print('{')
                    #print("  intent : '%s'" % inference.intent)
                    #print('  slots : {')
                    for slot, value in inference.slots.items():
                        if slot == "thebook":
                            thebook = value
                        elif slot == "thechapter":
                            thechapter = t2d.convert(value)
                        elif slot == "theverse":
                            theverse = t2d.convert(value)

                     #   print("    %s : '%s'" % (slot, value))
                   #     print("    %s : '%s'" % (slot, t2d.convert(value)))

                  #  print('  }')
                    #print('}\n')
                    link = ""
                    if theverse != 0:
                        print("%s %s:%s" % (thebook, str(thechapter), str(theverse))) #print the verse
                        link = "https://bible-api.com/%s+%s:%s" % (thebook, thechapter, theverse)
                    else:
                        print("%s %s" % (thebook, str(thechapter))) #print the verse
                        link = "https://bible-api.com/%s+%s" % (thebook, thechapter)

                    #f = urllib.request.urlopen(link)
                    response = requests.get(link)
                    json_data = json.loads(response.text)


                    #myfile = f.read()
                    print(response.json().get("text"))
                    #print("%s %s:%s" ("John", str(3), str(16))) #print the verse

                #else:
                 #   print("Didn't understand the command.\n")
    except KeyboardInterrupt:
        print('Stopping ...')
    finally:
        recorder.delete()
        rhino.delete()
        if wav_file is not None:
            wav_file.close()


if __name__ == '__main__':
    main()
