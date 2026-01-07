#!/usr/bin/env python
import warnings
from datetime import datetime
import os
from finacial_researcher.crew import FinacialResearcher

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# os.makedirs('output', exist_ok=True)

def run():
    """
    Run the crew.
    """
    inputs = {
       'company': 'Google'
    }

    try:
        result =FinacialResearcher().crew().kickoff(inputs=inputs)
        print('Fianl Report', result.raw)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")

if __name__ == '__main__':
    run()