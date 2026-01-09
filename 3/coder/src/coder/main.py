#!/usr/bin/env python
import warnings
from coder.crew import Coder
from dotenv import load_dotenv

load_dotenv(override=True)

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

assignment = 'Write a python program to calculate the first 10,000 terms \
    of this series, multiplying the total by 4: 1 - 1/3 + 1/5 - 1/7 + ...'

def run():
    inputs = {
        'assignment': assignment,
        }

    result = Coder().crew().kickoff(inputs=inputs)
    print(result.raw)
