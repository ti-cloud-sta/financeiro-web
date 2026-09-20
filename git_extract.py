import os
import zlib

git_objects_dir = '.git/objects'
target_filename = b'inadimplencia.component.html'
found_content = None

for root, _, files in os.walk(git_objects_dir):
    for file in files:
        if file in ['pack', 'info']: continue
        obj_path = os.path.join(root, file)
        try:
            with open(obj_path, 'rb') as f:
                compressed = f.read()
            decompressed = zlib.decompress(compressed)
            if target_filename in decompressed or b'<!-- Tab Pend\xc3\xaancias -->' in decompressed:
                if b'isDashboardLoading' in decompressed:
                    header, content = decompressed.split(b'\x00', 1)
                    if header.startswith(b'blob '):
                        print(f"Found match in {file}")
                        found_content = content
        except Exception as e:
            pass

if found_content:
    with open('frontend/src/app/pages/inadimplencia/inadimplencia.component.html', 'wb') as f:
        f.write(found_content)
    print("SUCCESSFULLY RESTORED FROM GIT OBJECTS!")
else:
    print("Not found in objects!")
