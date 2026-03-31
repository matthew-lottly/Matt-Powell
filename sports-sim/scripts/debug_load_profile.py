from pathlib import Path
import pstats

def main():
    p = Path("tuner_profile.prof")
    print("exists:", p.exists())
    print("cwd:", Path.cwd())
    try:
        s = pstats.Stats(str(p))
        print("loaded via str OK; entries:", len(s.stats))
    except Exception as e:
        print("err str:", e)
    try:
        s = pstats.Stats(p)
        print("loaded via Path OK; entries:", len(s.stats))
    except Exception as e:
        print("err path:", e)

if __name__ == '__main__':
    main()
