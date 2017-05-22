from org import parse
import org.write as write

from pprint import pprint

if __name__ == '__main__':
    from argparse import ArgumentParser

    p = ArgumentParser('orgmode')
    p.add_argument('file')
    p.add_argument('--profile', action='store_true')
    p.add_argument('--verbose', '-v', action='store_true')
    p.add_argument('--no-output', '-n', action='store_true')
    p.add_argument('--time', '-t', action='store_true')
    p.add_argument('--output-type', '-o', choices={'org', 'json'}, default='org')

    args = p.parse_args()

    if args.verbose:
        org.util.print_debug = True

    do_pprint = False
    #if args.output_type in {'json'}:
    #do_pprint = True

    filename = args.file
    with open(filename, 'r') as f:
        if args.profile:
            import profile
            profile.run('parse(f)', sort='cumtime')
        else:
            import time
            start_time = time.time()
            ast = parse(f)
            duration = time.time() - start_time
            s = write.dumps(ast, type=args.output_type)
            if not args.no_output:
                if do_pprint:
                    pprint(s, indent=2, width=160)
                else:
                    print(s)
                    #print(repr(ast))
            if args.time:
                print('%s s' % duration)
