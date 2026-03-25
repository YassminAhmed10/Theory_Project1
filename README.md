# Regex → DFA Converter

## 📌 Project Overview

This project implements a complete pipeline for converting a **Regular Expression (Regex)** into a **Deterministic Finite Automaton (DFA)** using the **Direct Method (Followpos Algorithm)**.

The system parses the input regex, constructs a syntax tree (AST), computes positional functions, builds the DFA directly, and visualizes the result graphically.

---

## 👥 Team Members

* **Yassmin Ahmed** – ID: 231001654
* **Zeina Mohamed** – ID: 231001039
* **Mario Sameh** – ID: 231001484
* **Kahed Yehia** – ID: 231001055

---

## 🎯 Features

* Convert Regex → DFA using the direct (followpos) method
* Supports standard regex operators:

  * Concatenation (implicit)
  * Alternation `|`
  * Kleene Star `*`
  * One-or-more `+`
  * Zero-or-one `?`
  * Grouping `()`
  * Escaped characters `\`
* Syntax Tree (AST) construction
* Followpos table generation
* DFA construction with transition table
* Optional DFA minimization (Hopcroft’s Algorithm)
* Graphical visualization of DFA using Graphviz
* String testing (accept / reject)

---

## 🧾 Input Format

The user enters a regular expression using standard notation.

### Examples:

```text
(a|b)*a
ab*c
(a|b)+
```

---

## 📤 Output Format

### 1. Graphical Output

* DFA diagram showing:

  * States
  * Transitions
  * Start state
  * Accept states
  * Dead state (if exists)

### 2. Textual Output

* Alphabet
* Number of states
* Start state
* Accepting states
* Dead state
* Transition table

### 3. Internal Data

* Syntax Tree
* Followpos table
* DFA construction steps
* Minimization report (optional)

### 4. Testing

* Input string → Accepted / Rejected

---

## ⚙️ Inside Mechanism

### 🔹 1. Regex Parsing

* Adds explicit concatenation operator `.`
* Appends end-marker `#`
* Converts regex into a Syntax Tree (AST)

---

### 🔹 2. Annotation Phase

Each node in the syntax tree is annotated with:

* `nullable`
* `firstpos`
* `lastpos`

Each leaf node is assigned a unique **position number**

---

### 🔹 3. Followpos Computation

* For concatenation `A . B`:

  * Add `firstpos(B)` to all positions in `lastpos(A)`

* For Kleene star `A*`:

  * Add `firstpos(A)` to all positions in `lastpos(A)`

---

### 🔹 4. DFA Construction

* Start state = `firstpos(root)`
* Each DFA state = set of positions
* Transition:

  * For each symbol `a`, union of followpos of positions labeled `a`
* Accept states:

  * Any state containing the position of `#`
* Dead state:

  * Added for missing transitions

---

### 🔹 5. DFA Minimization (Optional)

* Implemented using **Hopcroft’s Algorithm**
* Produces a minimal DFA

---

### 🔹 6. Visualization

* DFA is rendered using **Graphviz**
* States are drawn as nodes:

  * Accept states → double circles
* Transitions are labeled edges
* Output graph is displayed using Tkinter/PIL

---

## 🛠️ Technologies Used

* **Language:** Python 3
* **Core Algorithms:** Implemented from scratch (no external automata libraries)
* **GUI:** Tkinter
* **Graph Visualization:** Graphviz
* **Image Handling:** Pillow (PIL)

---

## 📦 Requirements

* Python 3.8+
* Graphviz (installed and added to PATH)

Install dependencies:

```bash
pip install graphviz pillow
```

---

## 📁 Project Structure

```text
├── task1_parser.py       # Regex parsing & AST construction
├── task2_followpos.py    # Position assignment & followpos computation
├── task3_dfa.py          # DFA construction & minimization
├── task4_gui.py          # GUI and visualization
├── assets/               # Generated images
└── README.md
```

---

## ▶️ How to Run

1. Install dependencies:

```bash
pip install graphviz pillow
```

2. Make sure Graphviz is installed and added to PATH

3. Run the application:

```bash
python task4_gui.py
```

---

## 🖼️ Screenshots

*(Add screenshots of GUI, DFA graph, followpos table, etc.)*

---

## ⚠️ Notes

* All core algorithms (parsing, followpos, DFA construction) are implemented manually
* Graphviz is used only for visualization
* No external automata or regex libraries are used

---

## 💡 Future Improvements

* Export DFA as PNG/PDF
* Step-by-step visualization
* Web-based interface
* Enhanced UI design

---

## 📚 References

* Theory of Computation course material
* Compiler Design (Syntax Trees & Automata)
* DFA Minimization Algorithms

---
