# Dallas County Courts Portal Scraper - Flow Diagrams

**Version:** 1.0  
**Last Updated:** 2025-11-27

This document provides comprehensive visual flow diagrams of the system architecture, execution flow, and data processing pipeline using Mermaid syntax.

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Main Execution Flow](#2-main-execution-flow)
3. [Concurrent Processing Flow](#3-concurrent-processing-flow)
4. [Single Attorney Scraping Flow](#4-single-attorney-scraping-flow)
5. [Case Extraction Loop](#5-case-extraction-loop)
6. [Captcha Resolution Flow](#6-captcha-resolution-flow)
7. [Data Flow Diagram](#7-data-flow-diagram)
8. [Error Handling & Recovery Flow](#8-error-handling--recovery-flow)
9. [Session Recovery Flow](#9-session-recovery-flow)
10. [Export Flow](#10-export-flow)

---

## 1. System Architecture Overview

### 1.1 Component Architecture

```mermaid
graph TB
    subgraph "Entry Layer"
        MAIN[main.py<br/>Application Entry Point]
    end
    
    subgraph "Orchestration Layer"
        POOL[scraper_pool.py<br/>Thread Pool Manager]
    end
    
    subgraph "Scraping Layer"
        SCRAPER1[Scraper Instance 1<br/>Attorney 1]
        SCRAPER2[Scraper Instance 2<br/>Attorney 2]
        SCRAPERn[Scraper Instance N<br/>Attorney N]
    end
    
    subgraph "Browser Layer"
        BROWSER1[Playwright Browser 1<br/>Isolated Context]
        BROWSER2[Playwright Browser 2<br/>Isolated Context]
        BROWSERn[Playwright Browser N<br/>Isolated Context]
    end
    
    subgraph "Support Modules"
        CAPTCHA[captcha_handler.py<br/>Captcha Resolution]
        EXTRACTOR[case_data_extractor.py<br/>Data Extraction]
        EXPORTER[result_exporter.py<br/>Export Engine]
        UTILS[utils.py<br/>Browser Setup & Utilities]
        CONFIG[config.py<br/>Configuration]
    end
    
    MAIN -->|Validates Config| CONFIG
    MAIN -->|Orchestrates| POOL
    MAIN -->|Exports Results| EXPORTER
    
    POOL -->|Spawns| SCRAPER1
    POOL -->|Spawns| SCRAPER2
    POOL -->|Spawns| SCRAPERn
    
    SCRAPER1 -->|Uses| BROWSER1
    SCRAPER2 -->|Uses| BROWSER2
    SCRAPERn -->|Uses| BROWSERn
    
    SCRAPER1 -->|Resolves| CAPTCHA
    SCRAPER1 -->|Extracts| EXTRACTOR
    SCRAPER2 -->|Resolves| CAPTCHA
    SCRAPER2 -->|Extracts| EXTRACTOR
    SCRAPERn -->|Resolves| CAPTCHA
    SCRAPERn -->|Extracts| EXTRACTOR
    
    SCRAPER1 -->|Setup| UTILS
    SCRAPER2 -->|Setup| UTILS
    SCRAPERn -->|Setup| UTILS
    
    POOL -->|Aggregates| MAIN
    MAIN -->|Writes| EXPORTER
    
    style MAIN fill:#e1f5ff
    style POOL fill:#fff4e1
    style EXPORTER fill:#e8f5e9
    style CAPTCHA fill:#fce4ec
    style EXTRACTOR fill:#f3e5f5
```

### 1.2 Module Dependencies

```mermaid
graph LR
    subgraph "Core Modules"
        MAIN[main.py]
        SCRAPER[scraper.py]
        POOL[scraper_pool.py]
    end
    
    subgraph "Support Modules"
        CAPTCHA[captcha_handler.py]
        EXTRACTOR[case_data_extractor.py]
        EXPORTER[result_exporter.py]
        UTILS[utils.py]
    end
    
    subgraph "Configuration"
        CONFIG[config.py]
    end
    
    MAIN -->|imports| POOL
    MAIN -->|imports| EXPORTER
    MAIN -->|imports| UTILS
    MAIN -->|imports| CONFIG
    
    POOL -->|imports| SCRAPER
    
    SCRAPER -->|imports| CAPTCHA
    SCRAPER -->|imports| EXTRACTOR
    SCRAPER -->|imports| UTILS
    SCRAPER -->|imports| CONFIG
    
    EXPORTER -->|imports| UTILS
    EXPORTER -->|imports| CONFIG
    
    UTILS -->|imports| CONFIG
    
    style MAIN fill:#e1f5ff
    style SCRAPER fill:#fff4e1
    style CONFIG fill:#f5f5f5
```

---

## 2. Main Execution Flow

### 2.1 Complete Application Flow

```mermaid
flowchart TD
    START([Start: python main.py]) --> LOG[Setup Logging]
    LOG --> VALIDATE{Validate<br/>Configuration}
    
    VALIDATE -->|Invalid| ERROR1[Log Error<br/>Exit]
    VALIDATE -->|Valid| DISPLAY[Display Config]
    
    DISPLAY --> POOL[Initialize Thread Pool<br/>run_all_attorneys_concurrent]
    
    POOL --> LOOP{For Each<br/>Attorney}
    
    LOOP -->|Next Attorney| WORKER[Create Worker Thread<br/>scrape_attorney_worker]
    WORKER --> SCRAPE[Run Scraper<br/>scraper.run]
    SCRAPE --> RESULT{Scraping<br/>Success?}
    
    RESULT -->|Success| COLLECT[Collect Results<br/>Thread-Safe Append]
    RESULT -->|Failure| LOG_ERROR[Log Error<br/>Continue]
    
    COLLECT --> LOOP
    LOG_ERROR --> LOOP
    
    LOOP -->|All Complete| AGGREGATE[Aggregate All Results]
    
    AGGREGATE --> CHECK{Results<br/>Found?}
    
    CHECK -->|Yes| EXPORT[Export Results<br/>export_results]
    CHECK -->|No| WARN[Log: No Cases Found]
    
    EXPORT --> SUCCESS([Success<br/>Results Exported])
    WARN --> END([End])
    ERROR1 --> END
    
    INTERRUPT[KeyboardInterrupt] --> PARTIAL[Export Partial Results]
    EXCEPTION[Exception] --> LOG_EXCEPTION[Log Exception]
    
    PARTIAL --> END
    LOG_EXCEPTION --> END
    
    START -.->|User Interrupt| INTERRUPT
    START -.->|Error| EXCEPTION
    
    style START fill:#c8e6c9
    style SUCCESS fill:#c8e6c9
    style ERROR1 fill:#ffcdd2
    style INTERRUPT fill:#fff9c4
    style EXCEPTION fill:#ffcdd2
```

---

## 3. Concurrent Processing Flow

### 3.1 Thread Pool Execution

```mermaid
sequenceDiagram
    participant Main as main.py
    participant Pool as scraper_pool.py
    participant Executor as ThreadPoolExecutor
    participant W1 as Worker Thread 1
    participant W2 as Worker Thread 2
    participant WN as Worker Thread N
    participant Results as Shared Results<br/>(Thread-Safe)
    
    Main->>Pool: run_all_attorneys_concurrent(attorneys)
    Pool->>Pool: Calculate num_workers = min(attorneys, MAX_WORKERS)
    Pool->>Executor: Create ThreadPoolExecutor(max_workers)
    
    loop For Each Attorney
        Pool->>Executor: Submit scrape_attorney_worker(attorney, index)
    end
    
    Executor->>W1: Execute Worker 1
    Executor->>W2: Execute Worker 2
    Executor->>WN: Execute Worker N
    
    par Parallel Execution
        W1->>W1: Create Scraper Instance 1
        W1->>W1: Run scraper.run()
        W1->>Results: Append results (with lock)
    and
        W2->>W2: Create Scraper Instance 2
        W2->>W2: Run scraper.run()
        W2->>Results: Append results (with lock)
    and
        WN->>WN: Create Scraper Instance N
        WN->>WN: Run scraper.run()
        WN->>Results: Append results (with lock)
    end
    
    W1->>Pool: Return (index, results, success, error)
    W2->>Pool: Return (index, results, success, error)
    WN->>Pool: Return (index, results, success, error)
    
    Pool->>Pool: Track exceptions per worker
    Pool->>Pool: Generate summary statistics
    Pool->>Main: Return aggregated results list
```

---

## 4. Single Attorney Scraping Flow

### 4.1 Complete Scraper Workflow

```mermaid
flowchart TD
    START([Start: Scraper Instance]) --> INIT[Initialize Browser<br/>setup_browser]
    
    INIT --> NAV[Navigate to Search Page<br/>BASE_URL]
    
    NAV -->|Failure| FAIL1[Return False]
    NAV -->|Success| EXPAND[Expand Advanced Options<br/>Best-Effort]
    
    EXPAND --> SELECT[Select 'Attorney Name' Filter]
    SELECT --> FILL[Fill Search Fields<br/>First Name & Last Name]
    
    FILL -->|Failure| FAIL2[Return False]
    FILL -->|Success| CAPTCHA{Resolve<br/>Captcha}
    
    CAPTCHA -->|Failure| FAIL3[Return False]
    CAPTCHA -->|Success| SUBMIT[Click Submit Button]
    
    SUBMIT -->|Failure| FAIL4[Return False]
    SUBMIT -->|Success| DATE_CHECK{Check Latest<br/>File Date}
    
    DATE_CHECK -->|Year < MIN_YEAR| FAIL5[Return False<br/>No Recent Cases]
    DATE_CHECK -->|Year >= MIN_YEAR<br/>or Unknown| PAGE_SIZE[Set Items Per Page<br/>200 rows]
    
    PAGE_SIZE --> FILTER[Get Case Type Rows<br/>Filter by CASE_TYPE]
    
    FILTER --> EMPTY{Has<br/>Cases?}
    EMPTY -->|No| SUCCESS1[Return True<br/>No Cases Found]
    EMPTY -->|Yes| PROCESS[Process Case Rows Loop]
    
    PROCESS --> CLEANUP[Cleanup Browser<br/>Resources]
    CLEANUP --> SUCCESS2[Return True<br/>Results Collected]
    
    FAIL1 --> CLEANUP
    FAIL2 --> CLEANUP
    FAIL3 --> CLEANUP
    FAIL4 --> CLEANUP
    FAIL5 --> CLEANUP
    
    style START fill:#c8e6c9
    style SUCCESS1 fill:#c8e6c9
    style SUCCESS2 fill:#c8e6c9
    style FAIL1 fill:#ffcdd2
    style FAIL2 fill:#ffcdd2
    style FAIL3 fill:#ffcdd2
    style FAIL4 fill:#ffcdd2
    style FAIL5 fill:#ffcdd2
```

---

## 5. Case Extraction Loop

### 5.1 Detailed Case Processing Flow

```mermaid
flowchart TD
    START([Start: Process Cases]) --> ROWS[Get Case Type Rows<br/>Filtered by CASE_TYPE]
    
    ROWS --> CHECK_EMPTY{Any<br/>Rows?}
    CHECK_EMPTY -->|No| DONE([Complete<br/>No Cases])
    CHECK_EMPTY -->|Yes| LOOP{For Each Row<br/>i = 0 to len-1}
    
    LOOP --> GET_CASE[Get Case Number<br/>from Row]
    GET_CASE --> DUPLICATE{Already<br/>Processed?}
    
    DUPLICATE -->|Yes| SKIP[Skip Case<br/>i++]
    DUPLICATE -->|No| CLICK[Click Case Link<br/>Navigate to Details]
    
    CLICK -->|Failure| SKIP
    CLICK -->|Success| KEYWORD{Check Charge<br/>Keywords}
    
    KEYWORD -->|Not Found| BACK1[Navigate Back<br/>Skip Extraction]
    KEYWORD -->|Found| EXTRACT[Extract Case Details<br/>extract_case_details]
    
    EXTRACT --> ADD[Add to Results<br/>Mark as Processed]
    ADD --> BACK2[Navigate Back<br/>to Results]
    
    BACK1 --> REFRESH[Refresh Row List<br/>DOM May Have Changed]
    BACK2 --> REFRESH
    
    REFRESH --> NAV_CHECK{Navigation<br/>Success?}
    
    NAV_CHECK -->|Failure| RECOVERY{Session<br/>Recovery<br/>Enabled?}
    NAV_CHECK -->|Success| LOOP
    
    RECOVERY -->|Yes| RECOVER[Attempt Session Recovery<br/>recover_session]
    RECOVERY -->|No| ERROR1[Return<br/>Stop Processing]
    
    RECOVER -->|Success| REFRESH
    RECOVER -->|Failure| ERROR1
    
    SKIP --> LOOP
    LOOP -->|All Processed| DONE
    
    style START fill:#e1f5ff
    style DONE fill:#c8e6c9
    style ERROR1 fill:#ffcdd2
    style RECOVER fill:#fff9c4
```

### 5.2 Case Detail Extraction Process

```mermaid
flowchart LR
    PAGE[Case Detail Page] --> GATE{Keyword<br/>Check}
    
    GATE -->|No Keywords| SKIP[Skip Case]
    GATE -->|Keywords Found| EXTRACT[Extract Details]
    
    EXTRACT --> CASE_NUM[Case Number<br/>Required]
    EXTRACT --> FILE_DATE[File Date<br/>Required]
    EXTRACT --> JUDGE[Judicial Officer<br/>Required]
    EXTRACT --> STATUS[Case Status<br/>Required]
    EXTRACT --> CHARGE[Charge Description<br/>Optional]
    EXTRACT --> BOND[Bond Amount<br/>Optional]
    EXTRACT --> DISP[Disposition<br/>Optional]
    EXTRACT --> SENT[Sentencing Info<br/>Optional]
    
    CASE_NUM --> VALIDATE{Required<br/>Fields<br/>Present?}
    FILE_DATE --> VALIDATE
    JUDGE --> VALIDATE
    STATUS --> VALIDATE
    
    VALIDATE -->|Missing| ERROR[Log Error<br/>Return Empty]
    VALIDATE -->|Present| ADD_ATTY[Add Attorney Info]
    
    ADD_ATTY --> RESULT[Append to Results<br/>List]
    
    RESULT --> RETURN([Return Case Data])
    ERROR --> RETURN
    SKIP --> RETURN
    
    style PAGE fill:#e1f5ff
    style RETURN fill:#c8e6c9
    style ERROR fill:#ffcdd2
```

---

## 6. Captcha Resolution Flow

### 6.1 Captcha Handling Decision Tree

```mermaid
flowchart TD
    START([Captcha Detected]) --> DETECT[detect_captcha<br/>Scan Page]
    
    DETECT --> FOUND{Captcha<br/>Found?}
    FOUND -->|No| SUCCESS1([No Captcha<br/>Continue])
    FOUND -->|Yes| SERVICE{Use<br/>Service?}
    
    SERVICE -->|No| MANUAL[Manual Solving<br/>solve_captcha_manually]
    SERVICE -->|Yes| HAS_KEY{API Key<br/>Valid?}
    
    HAS_KEY -->|No| MANUAL
    HAS_KEY -->|Yes| CHECK_FLAG{Manual Flag<br/>Set?}
    
    CHECK_FLAG -->|Yes| MANUAL
    CHECK_FLAG -->|No| BALANCE[Check Account Balance<br/>check_2captcha_balance]
    
    BALANCE --> BAL_OK{Balance<br/>Sufficient?}
    BAL_OK -->|No| SET_FLAG[Set Manual Flag<br/>Thread-Local]
    SET_FLAG --> MANUAL
    
    BAL_OK -->|Yes| SUBMIT[Submit to 2Captcha<br/>solve_recaptcha_v2_with_2captcha]
    
    SUBMIT --> POLL[Poll for Solution<br/>30-60 seconds]
    POLL --> SOLVED{Solution<br/>Ready?}
    
    SOLVED -->|No| TIMEOUT{Timeout?}
    TIMEOUT -->|Yes| SET_FLAG2[Set Manual Flag]
    TIMEOUT -->|No| POLL
    SET_FLAG2 --> MANUAL
    
    SOLVED -->|Yes| INJECT[Inject Token<br/>inject_recaptcha_token]
    INJECT --> VERIFY{Token<br/>Verified?}
    
    VERIFY -->|Yes| SUCCESS2([Captcha Solved<br/>Continue])
    VERIFY -->|No| MANUAL
    
    MANUAL --> CLICK[Click Checkbox<br/>Wait for User]
    CLICK --> POLL_MANUAL[Poll for Completion<br/>Check aria-checked]
    POLL_MANUAL --> DONE{Checkbox<br/>Checked?}
    
    DONE -->|Yes| SUCCESS3([Manual Solve Complete])
    DONE -->|No| TIMEOUT_MAN{Timeout?}
    TIMEOUT_MAN -->|Yes| FAIL([Captcha Failed])
    TIMEOUT_MAN -->|No| POLL_MANUAL
    
    style START fill:#e1f5ff
    style SUCCESS1 fill:#c8e6c9
    style SUCCESS2 fill:#c8e6c9
    style SUCCESS3 fill:#c8e6c9
    style FAIL fill:#ffcdd2
    style MANUAL fill:#fff9c4
```

---

## 7. Data Flow Diagram

### 7.1 End-to-End Data Flow

```mermaid
flowchart LR
    subgraph "Input"
        CONFIG[config.py<br/>ATTORNEYS<br/>CHARGE_KEYWORDS<br/>MINIMUM_CASE_YEAR]
    end
    
    subgraph "Processing"
        POOL[Thread Pool<br/>Concurrent Execution]
        SCRAPER1[Scraper 1]
        SCRAPER2[Scraper 2]
        SCRAPERn[Scraper N]
    end
    
    subgraph "Data Extraction"
        FILTER1[Date Filter<br/>Case Type Filter]
        EXTRACT1[Extract Case Details]
        FILTER2[Date Filter<br/>Case Type Filter]
        EXTRACT2[Extract Case Details]
        FILTERn[Date Filter<br/>Case Type Filter]
        EXTRACTn[Extract Case Details]
    end
    
    subgraph "Storage"
        RESULTS1[Results List 1<br/>In-Memory]
        RESULTS2[Results List 2<br/>In-Memory]
        RESULTSn[Results List N<br/>In-Memory]
    end
    
    subgraph "Aggregation"
        AGGREGATE[Aggregated Results<br/>Thread-Safe Collection]
    end
    
    subgraph "Transformation"
        DATAFRAME[pandas DataFrame<br/>Column Mapping]
    end
    
    subgraph "Output"
        EXCEL[Excel File<br/>Multi-Sheet]
        CSV[CSV File]
        JSON[JSON File]
    end
    
    CONFIG --> POOL
    POOL --> SCRAPER1
    POOL --> SCRAPER2
    POOL --> SCRAPERn
    
    SCRAPER1 --> FILTER1
    SCRAPER2 --> FILTER2
    SCRAPERn --> FILTERn
    
    FILTER1 --> EXTRACT1
    FILTER2 --> EXTRACT2
    FILTERn --> EXTRACTn
    
    EXTRACT1 --> RESULTS1
    EXTRACT2 --> RESULTS2
    EXTRACTn --> RESULTSn
    
    RESULTS1 --> AGGREGATE
    RESULTS2 --> AGGREGATE
    RESULTSn --> AGGREGATE
    
    AGGREGATE --> DATAFRAME
    DATAFRAME --> EXCEL
    DATAFRAME --> CSV
    DATAFRAME --> JSON
    
    style CONFIG fill:#e1f5ff
    style AGGREGATE fill:#fff4e1
    style DATAFRAME fill:#f3e5f5
    style EXCEL fill:#c8e6c9
    style CSV fill:#c8e6c9
    style JSON fill:#c8e6c9
```

### 7.2 Case Data Structure Flow

```mermaid
flowchart TD
    PORTAL[Dallas County Portal] --> RAW[Raw HTML Page]
    
    RAW --> PARSER[Playwright<br/>Page Parser]
    
    PARSER --> DETAILS[Case Detail Fields]
    
    DETAILS --> STRUCTURE{Structure<br/>Data}
    
    STRUCTURE --> CASE_NUM[case_number: str]
    STRUCTURE --> FILE_DATE[file_date: str]
    STRUCTURE --> JUDGE[judicial_officer: str]
    STRUCTURE --> STATUS[case_status: str]
    STRUCTURE --> TYPE[case_type: str]
    STRUCTURE --> CHARGE[charge_description: str]
    STRUCTURE --> BOND[bond_amount: str]
    STRUCTURE --> DISP[disposition: str]
    STRUCTURE --> SENT[sentencing_info: str]
    
    CASE_NUM --> DICT[Case Dictionary]
    FILE_DATE --> DICT
    JUDGE --> DICT
    STATUS --> DICT
    TYPE --> DICT
    CHARGE --> DICT
    BOND --> DICT
    DISP --> DICT
    SENT --> DICT
    
    DICT --> ATTY[Add Attorney Fields<br/>attorney_name<br/>attorney_first_name<br/>attorney_last_name]
    
    ATTY --> RESULT[Complete Case Record]
    
    RESULT --> COLLECT[Collect in Results List]
    
    style PORTAL fill:#e1f5ff
    style RESULT fill:#c8e6c9
```

---

## 8. Error Handling & Recovery Flow

### 8.1 Error Handling Strategy

```mermaid
flowchart TD
    OPERATION[Any Operation] --> TRY{Try<br/>Execute}
    
    TRY -->|Success| CONTINUE[Continue<br/>Next Step]
    TRY -->|Exception| CATCH{Catch<br/>Exception}
    
    CATCH --> TYPE{Exception<br/>Type?}
    
    TYPE -->|Config Error| CONFIG_ERR[Log Error<br/>Exit with Message]
    TYPE -->|Navigation Error| NAV_ERR[Log Error<br/>Return False]
    TYPE -->|Captcha Error| CAPTCHA_ERR{Retry<br/>Available?}
    TYPE -->|Extraction Error| EXTRACT_ERR[Log Error<br/>Skip Case<br/>Continue Loop]
    TYPE -->|Browser Error| BROWSER_ERR[Log Error<br/>Cleanup<br/>Propagate]
    TYPE -->|KeyboardInterrupt| INTERRUPT[Export Partial<br/>Results<br/>Graceful Exit]
    
    CAPTCHA_ERR -->|Yes| FALLBACK[Fallback to Manual<br/>Continue]
    CAPTCHA_ERR -->|No| CAPTCHA_FAIL[Return False<br/>Stop Scraping]
    
    EXTRACT_ERR --> CONTINUE
    FALLBACK --> CONTINUE
    
    NAV_ERR --> RECOVERY{Session<br/>Recovery<br/>Enabled?}
    
    RECOVERY -->|Yes| ATTEMPT[Attempt Recovery<br/>recover_session]
    RECOVERY -->|No| FAIL[Return False]
    
    ATTEMPT --> RECOVERY_SUCCESS{Recovery<br/>Success?}
    
    RECOVERY_SUCCESS -->|Yes| CONTINUE
    RECOVERY_SUCCESS -->|No| FAIL
    
    CONFIG_ERR --> END1([Exit])
    CAPTCHA_FAIL --> END2([Stop Scraping])
    FAIL --> END2
    INTERRUPT --> END3([Graceful Exit])
    CONTINUE --> END4([Continue Processing])
    
    style OPERATION fill:#e1f5ff
    style CONTINUE fill:#c8e6c9
    style CONFIG_ERR fill:#ffcdd2
    style CAPTCHA_FAIL fill:#ffcdd2
    style FAIL fill:#ffcdd2
    style INTERRUPT fill:#fff9c4
    style RECOVERY fill:#fff9c4
```

---

## 9. Session Recovery Flow

### 9.1 Recovery Process

```mermaid
flowchart TD
    ERROR([Navigation Error<br/>or Exception]) --> CHECK{ENABLE_SESSION<br/>_RECOVERY?}
    
    CHECK -->|No| STOP([Stop Processing])
    CHECK -->|Yes| CLEANUP[Cleanup Current<br/>Browser Resources]
    
    CLEANUP --> RETRY{Retry<br/>Count < 6?}
    
    RETRY -->|No| FAIL([Recovery Failed<br/>Max Retries])
    RETRY -->|Yes| WAIT[Wait 2 seconds]
    
    WAIT --> RESTART[Reinitialize Browser<br/>setup_browser]
    
    RESTART --> NAV[Navigate to Search Page]
    NAV -->|Failure| RETRY
    
    NAV -->|Success| EXPAND[Expand Advanced Options]
    EXPAND --> SELECT[Select Attorney Name Filter]
    SELECT --> FILL[Fill Search Fields]
    FILL -->|Failure| RETRY
    
    FILL -->|Success| CAPTCHA[Resolve Captcha]
    CAPTCHA -->|Failure| RETRY
    CAPTCHA -->|Success| SUBMIT[Submit Search]
    
    SUBMIT -->|Failure| RETRY
    SUBMIT -->|Success| PAGE_SIZE[Set Items Per Page]
    
    PAGE_SIZE --> VALIDATE{Successfully<br/>Recovered?}
    
    VALIDATE -->|No| RETRY
    VALIDATE -->|Yes| SKIP[Skip Already<br/>Processed Cases<br/>Using processed_case_numbers]
    
    SKIP --> CONTINUE([Continue from<br/>Last Position])
    
    style ERROR fill:#ffcdd2
    style FAIL fill:#ffcdd2
    style CONTINUE fill:#c8e6c9
    style RETRY fill:#fff9c4
```

---

## 10. Export Flow

### 10.1 Result Export Process

```mermaid
flowchart TD
    START([Results Available]) --> CHECK{Results<br/>Empty?}
    
    CHECK -->|Yes| EMPTY[Print: No Results<br/>Return]
    CHECK -->|No| CREATE[Create DataFrame<br/>pandas.DataFrame]
    
    CREATE --> RENAME[Rename Columns<br/>User-Friendly Titles]
    RENAME --> REORDER[Reorder Columns<br/>Logical Order]
    REORDER --> TIMESTAMP[Generate Timestamp<br/>YYYYMMDD_HHMMSS]
    
    TIMESTAMP --> FORMAT{Output<br/>Format?}
    
    FORMAT -->|Excel| EXCEL[Export Excel<br/>export_excel]
    FORMAT -->|CSV| CSV[Export CSV<br/>export_csv]
    FORMAT -->|JSON| JSON[Export JSON<br/>export_json]
    FORMAT -->|Unknown| DEFAULT[Default to Excel]
    
    EXCEL --> SHEETS[Create Sheets<br/>All Cases + Per Attorney]
    SHEETS --> FORMATTING[Format Sheets<br/>Column Widths<br/>Header Styling]
    FORMATTING --> FILE1[Save .xlsx File]
    
    CSV --> FILE2[Save .csv File]
    JSON --> FILE3[Save .json File]
    DEFAULT --> EXCEL
    
    FILE1 --> SUMMARY[Print Summary<br/>Cases by Attorney<br/>Column List]
    FILE2 --> SUMMARY
    FILE3 --> SUMMARY
    
    SUMMARY --> DONE([Export Complete])
    EMPTY --> DONE
    
    style START fill:#e1f5ff
    style DONE fill:#c8e6c9
    style EXCEL fill:#c8e6c9
```

---

## Diagram Legend

### Node Types

- **Rectangle (`[ ]`)**: Process or action
- **Diamond (`{ }`)**: Decision point or condition
- **Rounded Rectangle (`([ ])`)**: Start/End points
- **Parallelogram**: Data input/output
- **Double Rectangle**: Sub-process or external system

### Arrow Types

- **Solid Arrow (`-->`)**: Normal flow
- **Dashed Arrow (`-.->`)**: Exception or interrupt flow
- **Labeled Arrow (`--Label-->`)**: Conditional branch with label

### Color Coding

- 🟢 **Green**: Success states, completion points
- 🔴 **Red**: Error states, failure points
- 🟡 **Yellow**: Warning states, recovery attempts
- 🔵 **Blue**: Entry points, initialization
- 🟣 **Purple**: Data transformation points
- ⚪ **White/Gray**: Standard processes

---

## Key Behavioral Notes

### Execution Characteristics

1. **Concurrent Processing**: Multiple attorneys are processed simultaneously using thread pools, each with isolated browser instances
2. **Error Isolation**: Failures in one attorney's processing do not affect others
3. **Session Recovery**: Navigation failures trigger automatic recovery attempts when enabled
4. **Partial Result Preservation**: Interruptions preserve and export any collected results

### Filtering Strategy

1. **Date Filtering**: Early exit if newest case doesn't meet minimum year requirement (prevents processing stale data)
2. **Case Type Filtering**: Only rows containing configured case type (default: "FELONY") are processed
3. **Charge Keyword Filtering**: Applied at case detail level - cases without matching keywords are skipped entirely

### Resource Management

1. **Browser Isolation**: Each attorney gets independent browser context
2. **Automatic Cleanup**: Browser resources are cleaned up in `finally` blocks
3. **Thread Safety**: Result aggregation uses locks to prevent race conditions

### Data Flow

1. **In-Memory Accumulation**: Results collected during scraping, exported at completion
2. **Thread-Safe Collection**: Concurrent results safely merged using locking mechanisms
3. **Structured Output**: Data transformed to pandas DataFrame with user-friendly column names

---

**Diagram Version**: 1.0  
**Last Updated**: 2025-11-27
**Maintainer**: Jin

For detailed technical specifications, refer to `TECHNICAL_DOCUMENTATION.md`.
