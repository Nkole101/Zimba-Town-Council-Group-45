# Detection profile: db-unza26-csc4792-zimba_town_council_cdf_projects.csv

## Before cleaning

### head

```text
project_id                              project_name    sector constituency funding_source  funding_amount_zmw    status date_reported                                                                                                                                             description                             source_url
   ZTC-001    2023 CDF cooperative and company loans     other    Mapatizya            CDF                 NaN completed    2023-11-02             Loans were disbursed to 26 cooperatives and companies. The amount is left blank because the source prints the malformed figure K2, 93, 400. https://www.zimbacouncil.gov.zm/?p=911
   ZTC-002      2023 CDF women and youth club grants     other    Mapatizya            CDF           2143990.0 completed    2023-11-02                        K2,143,990 in grants was awarded to 65 women and youth clubs. Completed refers to the reported award, not subsequent activities. https://www.zimbacouncil.gov.zm/?p=911
   ZTC-003  Mapatizya 2620 school desks distribution education    Mapatizya            CDF           2887051.0 completed    2023-11-02 Distribution of 2,620 desks procured under 2022 and 2023 CDF was launched. The printed amount K 2, 887,051 is normalized by removing spaces and commas. https://www.zimbacouncil.gov.zm/?p=911
   ZTC-004 Cikuyu Primary School 1x3 classroom block education Chalimongela            CDF                 NaN completed    2023-11-27                                                                The classroom block was listed among completed 2022 CDF projects awaiting commissioning. https://www.zimbacouncil.gov.zm/?p=982
   ZTC-005                        Mbwiko Ward clinic    health       Mbwiko            CDF                 NaN completed    2023-11-27                                                            A clinic in Mbwiko Ward was listed among completed 2022 CDF projects awaiting commissioning. https://www.zimbacouncil.gov.zm/?p=982
```

### info

```text
<class 'pandas.DataFrame'>
RangeIndex: 44 entries, 0 to 43
Data columns (total 10 columns):
 #   Column              Non-Null Count  Dtype  
---  ------              --------------  -----  
 0   project_id          44 non-null     str    
 1   project_name        44 non-null     str    
 2   sector              44 non-null     str    
 3   constituency        42 non-null     str    
 4   funding_source      44 non-null     str    
 5   funding_amount_zmw  11 non-null     float64
 6   status              40 non-null     str    
 7   date_reported       44 non-null     str    
 8   description         44 non-null     str    
 9   source_url          44 non-null     str    
dtypes: float64(1), str(9)
memory usage: 3.6 KB

```

### describe

```text
       project_id                            project_name     sector constituency funding_source  funding_amount_zmw   status date_reported                                                                               description                               source_url
count          44                                      44         44           42             44        1.100000e+01       40            44                                                                                        44                                       44
unique         44                                      44          6           15              1                 NaN        4            15                                                                                        43                                       19
top       ZTC-001  2023 CDF cooperative and company loans  education    Mapatizya            CDF                 NaN  planned    2026-02-26  The classroom block was listed among completed 2022 CDF projects awaiting commissioning.  https://www.zimbacouncil.gov.zm/?p=4132
freq            1                                       1         16           16             44                 NaN       20            10                                                                                         2                                       10
mean          NaN                                     NaN        NaN          NaN            NaN        1.304800e+06      NaN           NaN                                                                                       NaN                                      NaN
std           NaN                                     NaN        NaN          NaN            NaN        8.535203e+05      NaN           NaN                                                                                       NaN                                      NaN
min           NaN                                     NaN        NaN          NaN            NaN        2.400000e+05      NaN           NaN                                                                                       NaN                                      NaN
25%           NaN                                     NaN        NaN          NaN            NaN        7.000000e+05      NaN           NaN                                                                                       NaN                                      NaN
50%           NaN                                     NaN        NaN          NaN            NaN        1.265907e+06      NaN           NaN                                                                                       NaN                                      NaN
75%           NaN                                     NaN        NaN          NaN            NaN        1.922924e+06      NaN           NaN                                                                                       NaN                                      NaN
max           NaN                                     NaN        NaN          NaN            NaN        2.887051e+06      NaN           NaN                                                                                       NaN                                      NaN
```

## After cleaning

### head

```text
project_id                              project_name    sector constituency funding_source  funding_amount_zmw    status date_reported                                                                                                                                             description                             source_url                                                                                                           description_clean
   ZTC-001    2023 CDF cooperative and company loans     other    Mapatizya            CDF                 NaN completed    2023-11-02             Loans were disbursed to 26 cooperatives and companies. The amount is left blank because the source prints the malformed figure K2, 93, 400. https://www.zimbacouncil.gov.zm/?p=911                loans disbursed 26 cooperatives companies amount left blank because source prints malformed figure k2 93 400
   ZTC-002      2023 CDF women and youth club grants     other    Mapatizya            CDF           2143990.0 completed    2023-11-02                        K2,143,990 in grants was awarded to 65 women and youth clubs. Completed refers to the reported award, not subsequent activities. https://www.zimbacouncil.gov.zm/?p=911                    k2 143 990 grants awarded 65 women youth clubs completed refers reported award not subsequent activities
   ZTC-003  Mapatizya 2620 school desks distribution education    Mapatizya            CDF           2887051.0 completed    2023-11-02 Distribution of 2,620 desks procured under 2022 and 2023 CDF was launched. The printed amount K 2, 887,051 is normalized by removing spaces and commas. https://www.zimbacouncil.gov.zm/?p=911 distribution 2 620 desks procured under 2022 2023 cdf launched printed amount k 2 887 051 normalized removing spaces commas
   ZTC-004 Cikuyu Primary School 1x3 classroom block education Chalimongela            CDF                 NaN completed    2023-11-27                                                                The classroom block was listed among completed 2022 CDF projects awaiting commissioning. https://www.zimbacouncil.gov.zm/?p=982                                             classroom block listed among completed 2022 cdf projects awaiting commissioning
   ZTC-005                        Mbwiko Ward clinic    health       Mbwiko            CDF                 NaN completed    2023-11-27                                                            A clinic in Mbwiko Ward was listed among completed 2022 CDF projects awaiting commissioning. https://www.zimbacouncil.gov.zm/?p=982                                          clinic mbwiko ward listed among completed 2022 cdf projects awaiting commissioning
```

### info

```text
<class 'pandas.DataFrame'>
RangeIndex: 44 entries, 0 to 43
Data columns (total 11 columns):
 #   Column              Non-Null Count  Dtype         
---  ------              --------------  -----         
 0   project_id          44 non-null     str           
 1   project_name        44 non-null     str           
 2   sector              44 non-null     string        
 3   constituency        42 non-null     str           
 4   funding_source      44 non-null     str           
 5   funding_amount_zmw  11 non-null     float64       
 6   status              44 non-null     string        
 7   date_reported       44 non-null     datetime64[us]
 8   description         44 non-null     str           
 9   source_url          44 non-null     str           
 10  description_clean   44 non-null     str           
dtypes: datetime64[us](1), float64(1), str(7), string(2)
memory usage: 3.9 KB

```

### describe

```text
       project_id                            project_name     sector constituency funding_source  funding_amount_zmw   status               date_reported                                                                               description                               source_url                                                                description_clean
count          44                                      44         44           42             44        1.100000e+01       44                          44                                                                                        44                                       44                                                                               44
unique         44                                      44          6           15              1                 NaN        5                         NaN                                                                                        43                                       19                                                                               43
top       ZTC-001  2023 CDF cooperative and company loans  education    Mapatizya            CDF                 NaN  planned                         NaN  The classroom block was listed among completed 2022 CDF projects awaiting commissioning.  https://www.zimbacouncil.gov.zm/?p=4132  classroom block listed among completed 2022 cdf projects awaiting commissioning
freq            1                                       1         16           16             44                 NaN       20                         NaN                                                                                         2                                       10                                                                                2
mean          NaN                                     NaN        NaN          NaN            NaN        1.304800e+06      NaN  2025-07-03 20:10:54.545454                                                                                       NaN                                      NaN                                                                              NaN
min           NaN                                     NaN        NaN          NaN            NaN        2.400000e+05      NaN         2023-11-02 00:00:00                                                                                       NaN                                      NaN                                                                              NaN
25%           NaN                                     NaN        NaN          NaN            NaN        7.000000e+05      NaN         2024-11-26 18:00:00                                                                                       NaN                                      NaN                                                                              NaN
50%           NaN                                     NaN        NaN          NaN            NaN        1.265907e+06      NaN         2025-12-09 12:00:00                                                                                       NaN                                      NaN                                                                              NaN
75%           NaN                                     NaN        NaN          NaN            NaN        1.922924e+06      NaN         2026-02-26 00:00:00                                                                                       NaN                                      NaN                                                                              NaN
max           NaN                                     NaN        NaN          NaN            NaN        2.887051e+06      NaN         2026-04-27 00:00:00                                                                                       NaN                                      NaN                                                                              NaN
std           NaN                                     NaN        NaN          NaN            NaN        8.535203e+05      NaN                         NaN                                                                                       NaN                                      NaN                                                                              NaN
```
