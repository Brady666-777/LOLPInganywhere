import sys

if __name__ == '__main__':
    if sys.platform != 'win32' and '--smoke-test' not in sys.argv:
        raise SystemExit('LoLPing Windows requires Windows 10/11. Use --smoke-test for UI checks.')
    from lolping.app import main
    raise SystemExit(main())
