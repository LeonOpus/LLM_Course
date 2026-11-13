import json
import os
import numpy as np
import Levenshtein  # For calculating edit distance
from openai import OpenAI, RateLimitError, APIError
from tqdm import tqdm # For progress bar
import time
import logging
from dotenv import load_dotenv

# --- Configuration ---
INPUT_JSON_FILE = 'extracted_llm_questions.json'
OUTPUT_JSON_FILE = 'deduplicated_questions.json'
OPENAI_EMBEDDING_MODEL = "text-embedding-ada-002" # Or "text-embedding-ada-002", or newer models



load_dotenv()

# --- Thresholds (Adjust these based on your needs) ---
# Normalized Edit Distance Threshold: Lower means more similar strings are considered duplicates.
# (0.0 = identical, 1.0 = completely different). A value like 0.1 means strings differing by <= 10% are duplicates.
NORMALIZED_EDIT_DISTANCE_THRESHOLD = 0.15

# Semantic Similarity Threshold: Higher means strings must be very close in meaning to be duplicates.
# Cosine similarity ranges from -1 to 1 (or 0 to 1 depending on vectors). High values (close to 1) mean high similarity.
SEMANTIC_SIMILARITY_THRESHOLD = 0.90 # A high threshold, requiring strong semantic overlap

# --- OpenAI Client Initialization ---
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if not client.api_key:
        raise ValueError("OpenAI API key not found. Set the OPENAI_API_KEY environment variable.")
except Exception as e:
    logging.error(f"Failed to initialize OpenAI client: {e}")
    exit(1)

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---

def get_embedding(text, model=OPENAI_EMBEDDING_MODEL, retries=3, delay=5):
    """Fetches text embedding from OpenAI with retry logic."""
    text = text.replace("\n", " ") # API recommendation
    if not text or not text.strip(): # Handle empty strings
        logging.warning("Attempted to get embedding for empty or whitespace-only string.")
        # Return a zero vector of the expected dimensionality, or handle as needed
        # Getting dimensionality requires a first successful call or knowing it beforehand.
        # Let's assume Ada-002 (1536) or text-embedding-3-small (1536) default.
        # For text-embedding-3-large it's 3072. Adjust if using a different model.
        default_dim = 1536 # Adjust if using text-embedding-3-large (3072)
        if model == "text-embedding-3-large":
             default_dim = 3072
        elif model == "text-embedding-ada-002":
             default_dim = 1536

        logging.warning(f"Returning zero vector of dimension {default_dim} for empty input.")
        return [0.0] * default_dim # Or handle differently (e.g., return None and skip)


    for attempt in range(retries):
        try:
            response = client.embeddings.create(input=[text], model=model)
            return response.data[0].embedding
        except RateLimitError:
            logging.warning(f"Rate limit exceeded. Retrying in {delay} seconds... (Attempt {attempt + 1}/{retries})")
            time.sleep(delay)
            delay *= 2 # Exponential backoff
        except APIError as e:
            logging.error(f"OpenAI API error: {e}. Retrying in {delay} seconds... (Attempt {attempt + 1}/{retries})")
            time.sleep(delay)
            delay *= 2
        except Exception as e:
            logging.error(f"An unexpected error occurred while getting embedding for '{text[:50]}...': {e}")
            if attempt == retries - 1:
                logging.error("Max retries reached. Skipping this text.")
                return None # Indicate failure
            time.sleep(delay) # Wait before retrying for general errors too
    return None # Return None if all retries fail

def calculate_normalized_edit_distance(s1, s2):
    """Calculates normalized Levenshtein distance."""
    if not s1 and not s2: return 0.0 # Both empty are identical
    if not s1 or not s2: return 1.0 # One empty, one not, are maximally different

    len1, len2 = len(s1), len(s2)
    max_len = max(len1, len2)
    if max_len == 0: return 0.0 # Should be covered above, but for safety

    distance = Levenshtein.distance(s1, s2)
    return distance / max_len

def calculate_cosine_similarity(vec1, vec2):
    """Calculates cosine similarity between two vectors."""
    vector1 = np.array(vec1)
    vector2 = np.array(vec2)

    # Check for zero vectors
    norm1 = np.linalg.norm(vector1)
    norm2 = np.linalg.norm(vector2)
    if norm1 == 0 or norm2 == 0:
        # If both are zero vectors, consider them identical (similarity 1)
        # If one is zero and the other isn't, they are dissimilar (similarity 0 or handle as error)
        return 1.0 if norm1 == norm2 else 0.0

    # Proceed with cosine similarity calculation
    similarity = np.dot(vector1, vector2) / (norm1 * norm2)
    # Clamp values slightly outside [-1, 1] due to potential floating point inaccuracies
    return np.clip(similarity, -1.0, 1.0)

# --- Main Deduplication Logic ---

def deduplicate_questions(input_file, output_file):
    """Loads questions, deduplicates based on criteria, saves unique ones."""
    logging.info(f"Loading questions from {input_file}...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            all_questions = json.load(f)
        logging.info(f"Loaded {len(all_questions)} questions.")
        if not isinstance(all_questions, list):
            raise TypeError("Input JSON is not a list.")
        # Basic cleaning: remove None, convert to string, strip whitespace
        original_count = len(all_questions)
        all_questions = [str(q).strip() for q in all_questions if q is not None and str(q).strip()]
        cleaned_count = len(all_questions)
        if original_count != cleaned_count:
            logging.info(f"Removed {original_count - cleaned_count} null or empty questions.")

    except FileNotFoundError:
        logging.error(f"Error: Input file '{input_file}' not found.")
        return
    except json.JSONDecodeError:
        logging.error(f"Error: Could not decode JSON from '{input_file}'.")
        return
    except TypeError as e:
         logging.error(f"Error: Input file {input_file} does not contain a list of strings. {e}")
         return
    except Exception as e:
        logging.error(f"An unexpected error occurred during loading: {e}")
        return

    unique_questions = []
    unique_embeddings = [] # Store embeddings of unique questions to avoid re-computation

    logging.info("Starting deduplication process...")
    for i, current_question in enumerate(tqdm(all_questions, desc="Processing questions")):
        if not current_question: # Skip empty strings that might have passed initial filter
             logging.debug(f"Skipping empty string at index {i}.")
             continue

        is_duplicate = False
        current_embedding = None # Calculate only if needed and not found by edit distance

        # Compare with already found unique questions
        # Use index loop for easier access to corresponding embedding
        for j in range(len(unique_questions)):
            existing_question = unique_questions[j]
            existing_embedding = unique_embeddings[j]

            # 1. Check Edit Distance (faster check first)
            norm_edit_dist = calculate_normalized_edit_distance(current_question, existing_question)
            if norm_edit_dist <= NORMALIZED_EDIT_DISTANCE_THRESHOLD:
                logging.debug(f"Duplicate found (Edit Distance): '{current_question}' vs '{existing_question}' (Dist: {norm_edit_dist:.3f})")
                is_duplicate = True
                break # Stop comparing this current_question

            # 2. Check Semantic Similarity (if edit distance wasn't close enough)
            # Calculate embedding for current question only once if needed
            if current_embedding is None:
                current_embedding = get_embedding(current_question)
                if current_embedding is None:
                    logging.warning(f"Could not get embedding for '{current_question[:50]}...'. Skipping semantic check for this question.")
                    # Decide how to handle this: treat as unique or skip entirely?
                    # Let's treat it as unique for now, as we can't compare semantically.
                    break # Break from inner loop comparing against unique ones, proceed to add it

            # Ensure we have both embeddings to compare
            if current_embedding and existing_embedding:
                 semantic_sim = calculate_cosine_similarity(current_embedding, existing_embedding)
                 if semantic_sim >= SEMANTIC_SIMILARITY_THRESHOLD:
                     logging.debug(f"Duplicate found (Semantic Sim): '{current_question}' vs '{existing_question}' (Sim: {semantic_sim:.3f})")
                     is_duplicate = True
                     break # Stop comparing this current_question

        # Add to unique list if no duplicate was found
        if not is_duplicate:
            unique_questions.append(current_question)
            # If we haven't calculated the embedding yet, do it now.
            if current_embedding is None:
                 current_embedding = get_embedding(current_question)

            # Only add the embedding if we successfully got one
            if current_embedding:
                 unique_embeddings.append(current_embedding)
            else:
                 # Handle cases where embedding failed for a question deemed unique
                 # We need a placeholder or handle this inconsistency.
                 # Adding a dummy embedding (like zeros) might skew future comparisons.
                 # Best might be to log and potentially exclude? Or add None?
                 # Let's add None and ensure cosine similarity handles it.
                 logging.warning(f"Adding unique question '{current_question[:50]}...' but failed to get its embedding.")
                 # Ensure calculate_cosine_similarity handles None gracefully if needed,
                 # Or adjust logic here. Current get_embedding returns zeros for empty strings,
                 # and None for API failures. Let's add the zero vector used for empty strings.
                 default_dim = 1536 # Adjust as per model
                 if OPENAI_EMBEDDING_MODEL == "text-embedding-3-large":
                     default_dim = 3072
                 unique_embeddings.append([0.0] * default_dim)


    logging.info(f"Deduplication complete. Found {len(unique_questions)} unique questions out of {cleaned_count}.")

    # Save the results
    logging.info(f"Saving unique questions to {output_file}...")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(unique_questions, f, ensure_ascii=False, indent=4)
        logging.info("Successfully saved deduplicated questions.")
    except Exception as e:
        logging.error(f"Error saving results to '{output_file}': {e}")

# --- Run the script ---
if __name__ == "__main__":
    deduplicate_questions(INPUT_JSON_FILE, OUTPUT_JSON_FILE)