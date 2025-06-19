#!/usr/bin/env python3
"""
Test Script for Content Extractor and Processor
===============================================

This script tests the full data pipeline by fetching data for specific pages,
running it through the ContentProcessor, and printing the final formatted
output without saving it to the database.
"""

import pprint
import traceback
from .content_extractor import ContentExtractor
from .content_processor import ContentProcessor
from .db_operations import DatabaseOperations
from .api_client import MediaWikiAPIClient

def test_full_processing(page_titles: list):
    """
    Tests the full data processing pipeline from extraction to formatting.
    """
    print("--- SCRIPT STARTED ---")
    
    # 1. Initialize classes
    try:
        print("1. Initializing classes...")
        client = MediaWikiAPIClient()
        db_ops = DatabaseOperations()
        extractor = ContentExtractor(client, db_ops)
        processor = ContentProcessor(db_ops)
        print("   - Extractor and Processor initialized.")

        # 2. Opening output file
        print(f"2. Opening output file: '{OUTPUT_FILE}'...")
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            print("   - Output file opened successfully.")
            for title in page_titles:
                try:
                    print(f"\n--- PROCESSING PAGE: {title} ---")
                    # 3. Extract raw data
                    print(f"3. Extracting raw data for '{title}'...")
                    page_data = extractor.extract_page_content(title)
                    if not page_data:
                        print(f"   - No data extracted for '{title}'. Skipping.")
                        continue
                    print(f"   - Raw data extracted for '{title}'.")

                    # 4. Process content
                    print(f"4. Processing content for '{title}'...")
                    formatted_content = processor.process_content(title, page_data)
                    print(f"   - Content processed. Final length: {len(formatted_content)} chars.")
                    
                    # 5. Write formatted content to file
                    print(f"5. Writing formatted content to file for '{title}'...")
                    f.write(f"\\n================================================================================\\n")
                    f.write(f"PROCESSING PAGE: {title}\\n")
                    f.write(f"================================================================================\\n")
                    f.write(f"✅ FINAL FORMATTED CONTENT:\\n")
                    f.write(f"--------------------------------------------------------------------------------\\n")
                    f.write(formatted_content)
                    f.write(f"\\n================================================================================\\n")
                    print(f"   - Content written to file.")

                except Exception as e:
                    print(f"\n❌❌❌ AN ERROR OCCURRED WHILE PROCESSING '{title}' ❌❌❌")
                    print(f"Error Type: {type(e).__name__}")
                    print(f"Error Details: {e}")
                    # Also print traceback to the console for debugging
                    traceback.print_exc()
                    continue

    except Exception as e:
        print(f"\n❌❌❌ AN UNEXPECTED ERROR OCCURRED ❌❌❌")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Details: {e}")
        print(f"\n--- TRACEBACK ---")
        traceback.print_exc()
        print("-----------------")
        
    finally:
        print("\n--- SCRIPT FINISHED ---")
        if 'f' in locals() and not f.closed:
            f.close()
            print("   - Output file closed.")
        print(f"✅ Processing complete. Data should be in '{OUTPUT_FILE}'.")


if __name__ == '__main__':
    # List of page titles to be processed
    PAGES_TO_PROCESS = [
        'USS Stardancer',
        '2025/06/06 Stardancer Log',
    ]
    
    OUTPUT_FILE = 'extraction_output.txt'

    print("--- Running main block ---")
    test_full_processing(PAGES_TO_PROCESS) 