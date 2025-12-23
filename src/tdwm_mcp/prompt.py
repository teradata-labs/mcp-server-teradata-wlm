PROMPTS = {"Create_new_rule": """Create new rule {RuleName} follow below steps to execute steps:

1. Create filter rule FILTER_IP_ADDRESS without any classification criteria.

CALL TDWM.TDWMCreateFilter(
   'MyFirstConfig',                        /* RulesetName */
   'FILTER_IP_ADDRESS',                    /* FilterName */
   'Filter by Client IP Address',          /* Description */
   NULL,                                   /* Attributes */
   'N'                                     /* ReplaceOption */);

   
2. Add classification criteria. Add client IP address criterion for client/user machine 55.77.100.224. Set ORing option to enable ClientIPAddrByClient check.

CALL TDWM.TDWMAddClassificationForRule(
   'MyFirstConfig',                        /* RulesetName */
   'FILTER_IP_ADDRESS',                    /* RuleName */
   'Address classification',               /* Description */
   'CLIENTADDR',                           /* ClassificationType */
   '55.77.100.224',                        /* ClassificationValue */
   'IO',                                   /* ClassificationOperator */
   'N'                                     /* ReplaceOption */);

3. Add client IP address criterion for client/user machine 55.77.100.225. Set ORing option to enable ClientIPAddrByClient check.

CALL TDWM.TDWMAddClassificationForRule( 
   'MyFirstConfig',                        /* RulesetName */
   'FILTER_IP_ADDRESS’,                    /* RuleName */
   'Address classification',               /* Description */
   'CLIENTADDR',                           /* ClassificationType */
   '55.77.100.225',                        /* ClassificationValue */
   'IO',                                   /* ClassificationOperator */
   'N'                                     /* ReplaceOption */);

4. Enable the filter in the default state. For a filter, the StateLimit is not applicable.

CALL TDWM.TDWMAddLimitForRuleState(
   'MyFirstConfig',                       /* RulesetName */
   'FILTER_IP_ADDRESS',                   /* RuleName */
   'DEFAULT',                             /* StateName */
   'Default limit',                       /* Description */
   NULL,                                  /* StateLimit */
   'E',                                   /* Action */
   'N'                                    /* ReplaceAction */);

5. Enable the filter rule (at the rule level).

CALL TDWM.TDWMManageRule(
   'MyFirstConfig',                     /* RulesetName */
   'FILTER_IP_ADDRESS',                 /* RuleName */
   'E'                                  /* Operation */);

6. Activate the MyFirstConfig ruleset with the new filter rule.

CALL TDWM.TDWMActivateRuleset(
  'MyFirstConfig',                      /* RulesetName */);
    """,
    "Create_System_Throttle_ARM": """

To create a system throttle, arrival rate meter, or filter rule {RuleName} in the TDWM system, follow these steps:

Understand all the required input parameters

The TASM rule attributes are for rule {RuleName}:

Ruleset name: {RuletName}
System throttle name: TableA_FTS
Description: Member throttle FTS on myDB.TableA from WebApp
Throttle type: Member
Qualifications:
Application: WebApp
Table: myDB.TableA
Subcriteria on myDB.TableA: Full Table Scan and minimum total process time of 3600 seconds
Limit: 1

The API call sequence to create new rule:

1. The desired ruleset name, MyFirstConfig, is known so it is not necessary to query the TDWM.Configurations table.
Create a system throttle called TableA_FTS without any classification criteria.

CALL TDWM.TDWMCreateSystemThrottle(
  'MyFirstConfig',    /* ruleset name */
  'TableA_FTS',       /* throttle name */
  'Member throttle FTS on myDB.TableA from WebApp' /* description */,
  'DM',               /* 'D': disable override, 'M': member type */
  'N'                 /* not replace */);

2. Add classification criteria.

2.1 Add application criterion:

CALL TDWM.TDWMAddClassificationForRule(
  'MyFirstConfig',               /* ruleset name */
  'TableA_FTS',                  /* rule name */
  'Application classification',  /* description */
  'APPL',                        /* application criterion type */
  'WebApp',                      /* APPL = WebApp */
  'I',                           /* Inclusion criterion APPL = WebApp */
  'N'                            /* Not a replace */);

2.2 Add table type criterion:

CALL TDWM.TDWMAddClassificationForRule(
  'MyFirstConfig',              /* ruleset name */
  'TableA_FTS',                 /* rule name */
  'Table classification',       /* description */
  'TABLE',                      /* table criterion type */
  'myDB.TableA',                /* TABLE = myDB.TableA */
  'I',                          /* Inclusion criterion */
  'N'                           /* Not a replace */);

3. Add sub-criteria for table criterion.

3.1 Add full table scan sub-criterion for target myDB.TableA:

CALL TDWM.TDWMAddClassificationForTarget( 
  'MyFirstConfig',              /* ruleset name */
  'TableA_FTS',                 /* rule name */
  'TABLE',                      /* Target: TABLE criterion type */
  'myDB.TableA',                /* Target: TABLE = myDB.TableA */
  'FTSCAN sub-criterion',       /* description */
  'FTSCAN',                     /* full table scan type */
  NULL,                         /* TargetValue not needed */ 
  'I',                          /* Inclusion criterion FTSCAN */
  'N'                           /* Not a replace */);

3.2 Add minimum step time sub-criterion for target myDB.TableA:

CALL TDWM.TDWMAddClassificationForTarget( 
  'MyFirstConfig',               /* ruleset name */
  'TableA_FTS',                  /* rule name */
  'TABLE',                       /* Target: TABLE criterion type */
  'myDB.TableA',                 /* Target: TABLE = myDB.TableA */
  'Min step time sub-criterion', /* description */
  'MINSTEPTIME',                 /* minimum step time */
  '3600',                        /* min >= 3600 seconds */
  'I',                           /* Inclusion criterion */
  'N'                            /* Not a replace */);

4. Set the default limit for the system throttle:

CALL TDWM.TDWMAddLimitForRuleState(
  'MyFirstConfig',               /* ruleset name */
  'TableA_FTS',                  /* rule name */
  'Default’,                     /* state name */
  'Default limit',               /* description */
  '1',                           /* limit */
  'D'                            /* delay */
  'N'                            /* Not a replace */);

5. Enable the system throttle:

CALL TDWM.TDWMManageRule(
  'MyFirstConfig',               /* ruleset name */
  'TableA_FTS',                  /* rule name */
  'E'                            /* enable throttle */);

6. Activate the {RuleName} ruleset with the new throttle.

CALL TDWM.TDWMActivateRuleset(
  'MyFirstConfig'      /* ruleset name */);
""",
"Delete_ThrottleARM_Filter" : """

Delete System Throttle, Arrival Rate Meter, or Filter by executing following steps:

1. Verify that {RuleName} exists in the TDWM.Configurations table.
If you want to delete a system throttle, arrival rate meter, or filter in a specific ruleset, retrieve the desired ruleset name from the TDWM.Configurations table.

2. Call the XSP TDWM.TDWMDeleteRule to delete a system throttle, arrival rate meter, or filter by specifying its name.

CALL TDWM.TDWMDeleteRule(
  'MyFirstConfig',         /* ruleset name */
  'Throttle_AcctDDL'       /* throttle name */);

3. Call the XSP TDWM.TDWMActivateRuleset to activate the updated MyFirstConfig ruleset, which no longer has the system throttle, arrival rate meter, or filter.

CALL TDWM.TDWMActivateRuleset(
  'MyFirstConfig'          /* ruleset name */);

    """
}