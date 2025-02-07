# **Student Schedule Optimization**

This project aims to efficiently assign students to work shifts while ensuring fairness, minimizing uncovered time slots, and balancing workloads. Using **linear programming** (PuLP), the system optimizes shift allocations based on availability and constraints.

---

## **📌 Project Overview**

Scheduling students for work shifts can be a complex problem due to conflicting availability, minimum/maximum work hours, and the need for balanced distribution. This project builds an **optimization model** that:
- Merges multiple **schedule files** into a unified dataset.
- **Assigns students** to time blocks based on availability and constraints.
- **Minimizes uncovered shifts** to maximize schedule efficiency.
- Generates **final schedules** in Excel format for easy review.

---

## **📁 Project Structure**

### **Main Components**
- **`merger.py`** – Merges multiple Excel schedule files into a single dataset.
- **`main.py`** – Implements the optimization algorithm to assign shifts.
- **`schedules.xlsx`** – Input dataset containing student availability.
- **`solution_assigned.xlsx`** – Optimized work schedule output.
- **`solution_uncovered.xlsx`** – Unassigned time slots due to constraints.
- **`LICENSE`** – Project licensing information.

---

## **⚙️ Installation & Setup**

### **Requirements**
Ensure you have Python 3 installed along with the necessary dependencies:

```bash
pip install pandas pulp openpyxl
```

### **Execution Steps**

1️⃣ **Merge schedule files (if applicable)**  
If multiple Excel files contain schedule data, merge them using:
```bash
python merger.py
```
This creates a single `schedules.xlsx` file from all `.xlsx` files in the `schedules/` directory.

2️⃣ **Run the scheduling optimization**  
Once the data is prepared, execute the optimization algorithm:
```bash
python main.py
```
This generates two output files:
- **`solution_assigned.xlsx`** – Optimized schedule with assigned shifts.
- **`solution_uncovered.xlsx`** – Blocks that remain unfilled.

---

## **📊 Optimization Constraints**

This project enforces several constraints to create an effective schedule:
- **Work Hour Limits** – Ensures students work within defined minimum (`minh`) and maximum (`maxh`) hours.
- **Balanced Workload** – Controls the overall average work hours per student (`avg_low`, `avg_high`).
- **Shift Structure** – Assigns 2–4 consecutive blocks per student for efficiency.
- **Fair Distribution** – Limits the number of overlapping workers per time block (`maxovl`).
- **Penalty for Excess Days** – Adds a small penalty (`day_cost`) to discourage excessive working days.

If no feasible solution is found, these parameters can be adjusted in `main.py` to allow flexibility.

---

## **🛠 Customization**

The scheduling constraints can be adjusted in `main.py`:
| Parameter | Description | Default Value |
|-----------|------------|---------------|
| `minh` | Minimum hours per student | `6` |
| `maxh` | Maximum hours per student | `20` |
| `avg_low` | Lower bound for average hours | `8` |
| `avg_high` | Upper bound for average hours | `12` |
| `maxovl` | Maximum students per block | `3` |
| `day_cost` | Penalty for working on additional days | `1` |

These values ensure fair scheduling while maintaining flexibility.

---

## **📜 License**

This project is open-source and follows the terms outlined in the `LICENSE` file. It is designed for educational and professional use, allowing modifications and adaptations as needed.
