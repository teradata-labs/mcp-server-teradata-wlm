# Static table with numeric index for reference
TDWM_CLASIFICATION_TYPE = [
    # idx, key, label, category, expected value
    (0,  "USER",       "User name",                         "Request Source", "User name"),
    (1,  "ACCT",       "Account name",                      "Request Source", "Account name"),
    (2,  "ACCTSTR",    "Account string",                    "Request Source", "Account string"),
    (3,  "PROFILE",    "Profile",                           "Request Source", "Profile name"),
    (4,  "APPL",       "Application name",                  "Request Source", "Application name"),
    (5,  "CLIENTADDR", "Client IP address",                 "Request Source", "Client IP address"),
    (6,  "CLIENTID",   "Client logon ID",                   "Request Source", "Client logon ID"),
    (7,  "DB",         "Database",                          "Target", "Database name"),
    (8,  "TABLE",      "Table",                             "Target", "Table name"),
    (9,  "VIEW",       "View",                              "Target", "View name"),
    (10, "MACRO",      "Macro",                             "Target", "Macro name"),
    (11, "SPROC",      "Stored procedure",                  "Target", "Stored procedure name"),
    (12, "FUNCTION",   "User-defined function",             "Target", "User-defined function name"),
    (13, "METHOD",     "User-defined method",               "Target", "User-defined method name"),
    (14, "SERVER",     "QueryGrid server",                  "Target", "QueryGrid server name"),
    (15, "STMT",       "Statement type",                    "Query Characteristics", "D = DDL, M = DML, S = SELECT, C = COLLECT STATISTICS, or a combination of D, M, S, C. Only ClassificationOperator 'I' allowed."),
    (16, "ALLAMP",     "All AMP request",                   "Query Characteristics", "Not applicable"),
    (17, "MSR",        "Multi statement request",           "Query Characteristics", "Integer (>= 2) specifying minimum statement count"),
    (18, "MINSTEPROWS","Minimum estimated step row count",  "Query Characteristics", "Integer (>= 1) specifying minimum estimated step row count"),
    (19, "MAXSTEPROWS","Maximum estimated step row count",  "Query Characteristics", "Integer (>= 1) specifying maximum estimated step row count" ),
    (20, "MINFINALROWS","Minimum estimated final row count","Query Characteristics", "Integer (>= 1) specifying minimum estimated final row count"),
    (21, "MAXFINALROWS","Maximum estimated final row count","Query Characteristics", "Integer (>= 1) specifying maximum estimated final row count"),
    (22, "MINSTEPTIME","Minimum estimated step processing time", "Query Characteristics", "Decimal (>= 0) specifying minimum estimated step processing time"),
    (23, "MAXSTEPTIME","Maximum estimated step processing time", "Query Characteristics", "Decimal (>= 1) specifying maximum estimated step processing time"),
    (24, "MINTOTALTIME","Minimum estimated total processing time", "Query Characteristics", "Decimal (>= 1) specifying minimum estimated total processing time"),
    (25, "MAXTOTALTIME","Maximum estimated total processing time", "Query Characteristics", "Decimal (>= 1) specifying maximum estimated total processing time"),
    (26, "JOIN",       "Join type",                         "Query Characteristics", "Only one of these values is allowed. N = no join, A = any join type, P = product join, Q = no product join, U = unconstrained product join, V = no unconstrained product join"),
    (27, "FTSCAN",     "Full table scan",                   "Query Characteristics", "Not applicable"),
    (28, "MEMORY",     "Memory usage",                      "Query Characteristics", "Only one of these values is allowed. I = increased, L = large, V = very large"),
    (29, "IPE",        "Incremental Planning and Execution","Query Characteristics", "Not applicable"),
    (30, "QUERYBAND",  "Query Band",                        "Query Band", "Query Band name-value pair"),
]

# Example function to retrieve by index
def get_tdwm_static_by_index(idx: int):
    return TDWM_CLASIFICATION_TYPE[idx] if 0 <= idx < len(TDWM_CLASIFICATION_TYPE) else None

# Example function to retrieve by key
def get_tdwm_static_by_key(key: str):
    for entry in TDWM_CLASIFICATION_TYPE:
        if entry[1] == key:
            return entry
    return None

def get_tdwm_key_by_label(label: str):
    """
    Retrieve the key for a given label.
    Returns the key if found, else None.
    """
    for entry in TDWM_CLASIFICATION_TYPE:
        if entry[2] == label:
            return entry[1]
    return None

  
