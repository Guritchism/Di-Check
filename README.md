# PDN Steganography Tool

This is a web application for hiding and revealing secret messages within PDN (Portable Draughts Notation) game notation using steganography techniques.

## Features

- **Encode**: Hide secret messages in PDN notation using three complementary methods:
  - Invisible characters after metadata entries
  - Leading zeros for single-digit moves
  - Odd/even seconds in clock notations
- **Decode**: Extract hidden messages from encoded PDN notation.

## How It Works

The application uses three steganography methods:

### Method 1: Metadata Steganography
- After each metadata line (like `[Event "Game Name"]`), the tool adds invisible whitespace characters.
- Each space represents a binary '0', and each tab represents a binary '1'.
- Each metadata line can store up to 4 bits of information.

### Method 2: Move Notation Steganography
- For moves with single-digit numbers (1-9), the tool can add a leading zero to encode information.
- Standard move: `3-8`
- Move with steganography: `03-08`
- If a move has a leading zero, it represents a binary '1'
- If a move doesn't have a leading zero, it represents a binary '0'

### Method 3: Clock Notation Steganography
- PDN files often contain clock notations in the format `{[%clock w0:14:00 B0:14:00]}`
- This method modifies the seconds value to encode bits:
  - Odd seconds (e.g., 01, 03, 59) represent a binary '1'
  - Even seconds (e.g., 00, 02, 58) represent a binary '0'
- The end of the message is marked by a terminator sequence (8 consecutive zeros)
- After the message and terminator, remaining clock notations are randomly modified to hide where the message ends

The application uses these methods in sequence, first trying to encode in the metadata, then in clock notations, and finally in move notations. This way, it maximizes the encoding capacity while maintaining the PDN's validity.

The sequence of these binary values can be translated into text using ASCII encoding.

## Setup

1. Install required packages:
```
pip install flask
```

2. Run the application:
```
python app.py
```

3. Open your browser and navigate to:
```
http://127.0.0.1:5000/
```

## Usage

### Encoding a Message

1. Navigate to the "Encode Message" tab
2. Paste your PDN game notation in the provided text area
3. Enter your secret message in the input field
4. Click the "Encode Message" button
5. Copy the encoded PDN from the result area

### Decoding a Message

1. Navigate to the "Decode Message" tab
2. Paste the encoded PDN game notation
3. Click the "Decode Message" button
4. View the extracted binary and decoded message in the result area

## Maximum Message Length

The tool calculates the maximum message length based on:
- Number of metadata lines × 4 bits per line (metadata capacity)
- Number of clock notations × 1 bit per notation (clock notation capacity)
- Number of single-digit numbers in moves (move notation capacity)
- Total bits ÷ 8 = Maximum number of characters

For example, if a PDN file has:
- 10 metadata lines: 10 × 4 = 40 bits
- 15 clock notations: 15 bits
- 20 single-digit numbers in moves: 20 bits
- Total capacity: 75 bits ÷ 8 = 9.375 characters (9 full characters)

## Technologies Used

- Backend: Flask (Python)
- Frontend: HTML, CSS, JavaScript
