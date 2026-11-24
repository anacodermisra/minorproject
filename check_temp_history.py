import os, time

temp_dir = r"C:\Users\Anand\AppData\Local\Temp"
files = [f for f in os.listdir(temp_dir) if any(k in f.lower() for k in ["report", "toc", "doc", "v5", "v4", "v6", "final"])]
for f in sorted(files, key=lambda x: os.path.getmtime(os.path.join(temp_dir, x))):
    fp = os.path.join(temp_dir, f)
    if os.path.isfile(fp):
        t = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(fp)))
        sz = os.path.getsize(fp)
        print(f"{t} | {sz:10d} bytes | {f}")
