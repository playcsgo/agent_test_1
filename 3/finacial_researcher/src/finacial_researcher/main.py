#!/usr/bin/env python
import warnings
from datetime import datetime
from finacial_researcher.crew import FinacialResearcher

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def run():
    """
    Run the crew.
    """
    current_date = datetime.now().strftime('%Y-%m-%d')

    inputs = {
       'company': 'Google',
       'current_date': current_date,
    }

    try:
        result =FinacialResearcher().crew().kickoff(inputs=inputs)
        print('Fianl Report', result.raw)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")

if __name__ == '__main__':
    run()