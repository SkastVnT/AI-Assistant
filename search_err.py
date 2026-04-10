import os
for root,dirs,files in os.walk("services/chatbot"):
    dirs[:] = [d for d in dirs if d not in ["__pycache__",".git","venv","node_modules"]]
    for f in files:
        if f.endswith((".py",".js",".html")):
            p = os.path.join(root,f)
            try:
                for i,line in enumerate(open(p,encoding="utf-8",errors="ignore")):
                    if "result received" in line.lower():
                        print(p, i+1, line.rstrip()[:100])
            except: pass

