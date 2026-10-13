import argparse
import json
from .evaluate import evaluate
from .benchmark import benchmark

def main():
    p=argparse.ArgumentParser();p.add_argument("command",choices=["eval","benchmark","preview"]);p.add_argument("--live",action="store_true");p.add_argument("--cases",type=int);p.add_argument("--iterations",type=int,default=120);p.add_argument("--upload-braintrust",action="store_true");args=p.parse_args()
    if args.command=="eval":
        r=evaluate(args.live,args.cases,args.upload_braintrust);print(json.dumps({"cases":r["cases"],"scores":r["scores"],"experiment":r.get("braintrust_experiment_url")}))
    elif args.command=="benchmark":
        r=benchmark(args.live,args.iterations);print(json.dumps({"results":r["results"]}))
    else:
        from .preview import build
        print(json.dumps(build()))

if __name__=="__main__":main()
