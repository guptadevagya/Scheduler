import pandas as pd
from datetime import datetime, timedelta
from pulp import (
    LpProblem,
    LpMinimize,
    LpVariable,
    LpStatus,
    lpSum,
    LpBinary,
    PULP_CBC_CMD
)

def loaddata(f):
    """
    Reads Excel data with columns:
        'Student Name', 'Day of Week', 'Class Start', 'Class End'
    Time format should match '%H:%M:%S' or '%H:%M' (adjust as needed).
    """
    df = pd.read_excel(f)
    # Adjust format to match your data
    df['Class Start'] = pd.to_datetime(df['Class Start'], format="%H:%M:%S").dt.time
    df['Class End']   = pd.to_datetime(df['Class End'],   format="%H:%M:%S").dt.time
    return df

def genblocks(days, start="07:30", end="17:30"):
    """
    Generate 1-hour blocks: (day, i, st, et)
        day = 'Monday', 'Tuesday', etc.
        i   = block index (0,1,2,...)
        st  = start time
        et  = end time
    """
    fmt = "%H:%M"
    st_time = datetime.strptime(start, fmt).time()
    en_time = datetime.strptime(end, fmt).time()

    blocks = []
    for d in days:
        cur = datetime.combine(datetime.today(), st_time)
        fin = datetime.combine(datetime.today(), en_time)
        i = 0
        while cur < fin:
            s = cur.time()
            e = (cur + timedelta(hours=1)).time()
            if e > en_time:
                break
            blocks.append((d, i, s, e))
            cur += timedelta(hours=1)
            i += 1
    return blocks

def freeblk(classes, d, s, e):
    """
    Return True if the student is free in block [s, e) on day d,
    i.e., no overlap with any (class_start, class_end) for that day.
    """
    for (day_of_week, cs, ce) in classes:
        if day_of_week == d:
            c1 = datetime.combine(datetime.today(), cs)
            c2 = datetime.combine(datetime.today(), ce)
            b1 = datetime.combine(datetime.today(), s)
            b2 = datetime.combine(datetime.today(), e)
            if c1 < b2 and c2 > b1:
                return False
    return True

def build_model(df,
                minh=6,        # Minimum total blocks (hours) per student
                maxh=20,       # Maximum total blocks (hours) per student
                avg_low=8,     # Overall average lower bound
                avg_high=12,   # Overall average upper bound
                maxovl=3,      # Max overlap
                day_cost=1     # Penalty for each day a student works
               ):
    """
    Build a PuLP model that enforces:
      - 2–4 consecutive blocks if a student works on any day
      - min <= student hours <= max
      - overall average across all students in [avg_low, avg_high]
      - "Soft" coverage: each block is either covered or marked uncovered
      - Up to maxovl staff per block
      - A small penalty day_cost for each day a student works
    """
    ds = sorted(df['Day of Week'].unique())
    # Generate 1-hour blocks
    blks = genblocks(ds)

    # student -> list of (Day of Week, Class Start, Class End)
    stmap = {}
    for s, g in df.groupby("Student Name"):
        stmap[s] = list(zip(g["Day of Week"], g["Class Start"], g["Class End"]))

    stus = list(stmap.keys())
    prob = LpProblem("sched", LpMinimize)

    # Decision variables
    x = {}        # x[s,d,i] = 1 if student s works block i on day d
    y = {}        # y[s,d]   = 1 if student s works at all on day d
    start2 = {}   # start2[s,d,i] = 1 if s starts a 2-block shift at i on day d
    start3 = {}   # start3[s,d,i] = 1 if s starts a 3-block shift
    start4 = {}   # start4[s,d,i] = 1 if s starts a 4-block shift
    u = {}        # u[d,i]        = 1 if block i on day d is uncovered

    # For grouping blocks by day
    day_blocks = {d: [] for d in ds}
    for (d, i, st, et) in blks:
        day_blocks[d].append((i, st, et))

    # Create variables
    for s in stus:
        for d in ds:
            y[(s,d)] = LpVariable(f"y_{s}_{d}", cat=LpBinary)

            # x[s,d,i]
            for (i, st, et) in day_blocks[d]:
                x[(s,d,i)] = LpVariable(f"x_{s}_{d}_{i}", cat=LpBinary)

            # startX variables where possible
            block_indices = [b[0] for b in day_blocks[d]]
            for (i, st, et) in day_blocks[d]:
                if (i+1) in block_indices:
                    start2[(s,d,i)] = LpVariable(f"start2_{s}_{d}_{i}", cat=LpBinary)
                if (i+2) in block_indices:
                    start3[(s,d,i)] = LpVariable(f"start3_{s}_{d}_{i}", cat=LpBinary)
                if (i+3) in block_indices:
                    start4[(s,d,i)] = LpVariable(f"start4_{s}_{d}_{i}", cat=LpBinary)

    for (d, i, st, et) in blks:
        u[(d,i)] = LpVariable(f"u_{d}_{i}", cat=LpBinary)

    # Objective: big penalty for uncovered blocks + small penalty for assigned blocks + day_cost for each day worked
    big_weight = 1000
    prob += (
        big_weight * lpSum(u[(d,i)] for (d,i,_,_) in blks)
        + lpSum(x[(s,d,i)] for s in stus for (d,i,_,_) in blks)
        + day_cost * lpSum(y[(s,d)] for s in stus for d in ds)
    ), "obj"

    # 1) Soft coverage
    for (d, i, st, et) in blks:
        prob += lpSum(x[(s,d,i)] for s in stus) + u[(d,i)] >= 1, f"cover_{d}_{i}"

    # 2) Overlap <= maxovl
    for (d, i, st, et) in blks:
        prob += lpSum(x[(s,d,i)] for s in stus) <= maxovl, f"ovl_{d}_{i}"

    # 3) Weekly min/max per student
    for s in stus:
        total_hrs = lpSum(x[(s,d,i)] for (d,i,_,_) in blks)
        prob += total_hrs >= minh, f"minH_{s}"
        prob += total_hrs <= maxh, f"maxH_{s}"

    # 4) Overall average in [avg_low, avg_high]
    N = len(stus)
    total_all = lpSum(x[(s,d,i)] for s in stus for (d,i,_,_) in blks)
    prob += total_all >= avg_low * N,  "AvgLow"
    prob += total_all <= avg_high * N, "AvgHigh"

    # 5) Busy check
    for s in stus:
        for d in ds:
            for (i, st, et) in day_blocks[d]:
                if not freeblk(stmap[s], d, st, et):
                    prob += x[(s,d,i)] == 0, f"busy_{s}_{d}_{i}"

    # 6) 2–4 consecutive blocks if y[s,d] = 1
    for s in stus:
        for d in ds:
            block_indices = [b[0] for b in day_blocks[d]]
            s2_list = [start2[(s,d,i)] for i in block_indices if (s,d,i) in start2]
            s3_list = [start3[(s,d,i)] for i in block_indices if (s,d,i) in start3]
            s4_list = [start4[(s,d,i)] for i in block_indices if (s,d,i) in start4]

            sum_x_day = lpSum(x[(s,d,i)] for i in block_indices)

            # Exactly 0 or 1 total shift
            prob += (lpSum(s2_list + s3_list + s4_list) == y[(s,d)]), f"shifts_{s}_{d}"

            # sum_x_day = 2*start2 + 3*start3 + 4*start4
            prob += sum_x_day == (
                2 * lpSum(s2_list) +
                3 * lpSum(s3_list) +
                4 * lpSum(s4_list)
            ), f"sumx_{s}_{d}"

            # link start2 => x[..i], x[..i+1], etc.
            for i in block_indices:
                if (s,d,i) in start2:
                    prob += x[(s,d,i)]   >= start2[(s,d,i)]
                    prob += x[(s,d,i+1)] >= start2[(s,d,i)]
                if (s,d,i) in start3:
                    prob += x[(s,d,i)]   >= start3[(s,d,i)]
                    prob += x[(s,d,i+1)] >= start3[(s,d,i)]
                    prob += x[(s,d,i+2)] >= start3[(s,d,i)]
                if (s,d,i) in start4:
                    prob += x[(s,d,i)]   >= start4[(s,d,i)]
                    prob += x[(s,d,i+1)] >= start4[(s,d,i)]
                    prob += x[(s,d,i+2)] >= start4[(s,d,i)]
                    prob += x[(s,d,i+3)] >= start4[(s,d,i)]

    return prob, x, y, u, blks, stus

def solve_and_extract(prob, x, y, u, blks, stus):
    """
    Solve the model and return two DataFrames:
      - sol_df: assigned blocks
      - uncovered_df: blocks marked uncovered
    """
    solver = PULP_CBC_CMD(msg=False)
    prob.solve(solver)

    print("Status:", LpStatus[prob.status])
    if LpStatus[prob.status] not in ['Optimal', 'Feasible']:
        return None

    # Build a DataFrame of assigned blocks
    rows = []
    for s in stus:
        for (d, i, st, et) in blks:
            if x[(s,d,i)].varValue == 1:
                rows.append({
                    "Student": s,
                    "Day": d,
                    "BlockIdx": i,
                    "Start": st.strftime("%H:%M"),
                    "End": et.strftime("%H:%M")
                })
    sol_df = pd.DataFrame(rows)

    if not sol_df.empty:
        # Each block is effectively 1 hour
        hrs = sol_df.groupby("Student")["BlockIdx"].count().to_dict()
        sol_df["TotalHrs"] = sol_df["Student"].map(hrs)
    else:
        sol_df["TotalHrs"] = 0

    # Sort nicely
    daymap = {"Monday":1, "Tuesday":2, "Wednesday":3, "Thursday":4, "Friday":5}
    sol_df["daynum"] = sol_df["Day"].map(daymap)
    sol_df.sort_values(["daynum","BlockIdx","Student"], inplace=True)
    sol_df.drop(columns=["daynum"], inplace=True)

    # Identify uncovered
    uncovered_rows = []
    for (d, i, st, et) in blks:
        if u[(d,i)].varValue == 1:
            uncovered_rows.append({
                "Day": d,
                "BlockIdx": i,
                "Start": st.strftime("%H:%M"),
                "End": et.strftime("%H:%M"),
                "Status": "Uncovered"
            })
    uncovered_df = pd.DataFrame(uncovered_rows)

    return sol_df, uncovered_df

def main():
    """
    Main entry point. 
    Try adjusting parameters if you get 'Infeasible'.
    """
    file = "schedules.xlsx"  # Your input file name
    df = loaddata(file)

    prob, x, y, u, blks, stus = build_model(
        df,
        minh=6,       # Min hours
        maxh=20,      # Max hours
        avg_low=8,    # Overall average lower bound
        avg_high=12,  # Overall average upper bound
        maxovl=3,     # Up to 3 people per block
        day_cost=1    # penalty for each day
    )

    result = solve_and_extract(prob, x, y, u, blks, stus)
    if result is None:
        print("No feasible (or partial-feasible) solution found.")
        return

    sol_df, uncovered_df = result

    print("=== ASSIGNED BLOCKS ===")
    print(sol_df)
    sol_df.to_excel("solution_assigned.xlsx", index=False)

    if not uncovered_df.empty:
        print("\n=== UNCOVERED BLOCKS ===")
        print(uncovered_df)
        uncovered_df.to_excel("solution_uncovered.xlsx", index=False)

if __name__ == "__main__":
    main()