#!/usr/bin/env python
import sys
import warnings
from datetime import datetime
from stock_picker.crew import StockPicker

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def run():
    """
    Run the crew.
    """
    current_date = datetime.now().strftime('%Y-%m-%d')
    inputs = {
        'sector': 'Technology',
        'current_date': str(current_date)
    }

    try:
        StockPicker().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")
