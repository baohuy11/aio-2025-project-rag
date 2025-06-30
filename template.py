import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s]: %(message)s:')

list_of_files = [
    "src/__init__.py",
    "src/qa_system/__init__.py",
    "src/qa_system/config.py",
    "src/qa_system/api/__init__.py",
    "src/qa_system/api/main.py",
    "src/qa_system/api/routers/__init__.py",
    "src/qa_system/api/routers/analytics.py",
    "src/qa_system/api/routers/lectures.py",
    "src/qa_system/api/routers/questions.py",
    "src/qa_system/models/__init__.py",
    "src/qa_system/models/answer.py",
    "src/qa_system/models/base.py",
    "src/qa_system/models/lecture.py",
    "src/qa_system/models/question.py",
    "src/qa_system/models/student_response.py",
    "src/qa_system/services/__init__.py",
    "src/qa_system/services/difficulty_adjuster.py",
    "src/qa_system/services/pptx_extractor.py",
    "src/qa_system/services/qa_generator.py",
    "src/front_end/__init__.py",
    "src/front_end/str_lit.py",
    "src/helper.py",
    "src/prompt.py",
    ".env",
    "setup.py",
    "app.py",
    "research/trials.ipynb",
    "test.py"
]

for filepath in list_of_files:
    filepath = Path(filepath)
    filedir, filename = os.path.split(filepath)


    if filedir !="":
        os.makedirs(filedir, exist_ok=True)
        logging.info(f"Creating directory; {filedir} for the file: {filename}")

    if (not os.path.exists(filepath)) or (os.path.getsize(filepath) == 0):
        with open(filepath, "w") as f:
            pass
            logging.info(f"Creating empty file: {filepath}")


    else:
        logging.info(f"{filename} is already exists")