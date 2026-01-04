When testing code that uses a  column type, it is strongly recommended to test against a real PostgreSQL instance rather than SQLite due to significant behavioral differences. SQLite has built-in JSON functions, but its  support is a binary format that is not compatible with PostgreSQL's . [1, 2, 3]  
Why Avoid SQLite for JSONB Testing 

• Type Mismatches: SQLite uses dynamic typing (type affinity), which is more forgiving than PostgreSQL's strict type checking. Code that passes in SQLite might fail in a production PostgreSQL environment. 
• Feature Differences: SQLite does not implement all PostgreSQL-specific SQL features or operators (e.g., , ) which your application logic may rely on. 
• Concurrency Issues: PostgreSQL has row-level locking, while SQLite locks the entire database file for writes, leading to different behavior under concurrent access. [1, 4, 5, 6]  

Recommended Testing Strategies 
Instead of "mocking" the database with an incompatible one, use a real PostgreSQL instance for integration tests and mock the database connection at a higher level (application logic layer) for unit tests. [7, 8]  
1. Integration Testing with Containerized PostgreSQL For reliable integration testing, spin up a dedicated PostgreSQL instance, ideally using Docker containers, for your test environment. This ensures your test environment exactly mirrors production. 

• Process: 

	• Use a tool like Docker or Testcontainers to start a specific version of a PostgreSQL container before your test suite runs. 
	• Configure your test application to connect to this containerized database instance. 
	• Use migration scripts or seeding classes to populate the database with test data. 
	• Ensure the database state is reset (e.g., via transactions or fresh setup) before each test or test suite run. [12, 13, 14, 15, 16]  

2. Unit Testing by Mocking the Data Access Layer For fast unit tests of your business logic, mock the data access layer (repository or service layer), assuming the persistence layer itself has already been tested via integration tests. 

• Process: 

	• Structure your code with a clear separation between business logic (functional core) and data access (imperative shell). 
	• Use a mocking framework specific to your programming language (e.g., Jest in JavaScript,  in Python) to mock the database connection or repository class methods. 
	• Define the expected input and output for these mocked methods (including the  data structure) to test your application's logic in isolation. [18, 19, 20, 21, 22]  

3. Using ORM-specific Compatibility Layers If you use an Object-Relational Mapper (ORM) like SQLAlchemy, you may be able to use type variants to handle database-specific types. This approach still carries risks due to functional differences beyond data types. 

• Example (SQLAlchemy): [23, 25, 26]  

In summary, using SQLite to mock PostgreSQL  functionality is generally not recommended due to fundamental incompatibilities that compromise test reliability. Use a real PostgreSQL instance for accurate testing. [1, 27]  

AI responses may include mistakes.

[1] https://medium.com/@carlotasotos/beyond-database-mocks-how-to-spin-up-real-postgres-testing-environments-in-seconds-7492eb3c8bd0
[2] https://news.ycombinator.com/item?id=38540421
[3] https://stackoverflow.com/questions/72698145/postgres-jsonb-not-compatible-with-sqlite-testing-environment
[4] https://neon.com/blog/testing-sqlite-postgres
[5] https://www.reddit.com/r/golang/comments/11mv4ki/dont_mock_the_database/
[6] https://neon.com/guides/flask-test-on-branch
[7] https://www.reddit.com/r/csharp/comments/t4xaqe/how_would_i_mock_the_following_for_unit_testing/
[8] https://knasmueller.net/gitlab-postgresql-testing-pipeline
[9] https://stackoverflow.com/questions/72698145/postgres-jsonb-not-compatible-with-sqlite-testing-environment
[10] https://jelvix.com/blog/java-integration-testing
[11] https://qawerk.com/blog/the-full-back-end-testing-checklist-from-qawerk/
[12] https://www.youtube.com/watch?v=g4RQVMtLL1U
[13] https://softwareengineering.stackexchange.com/questions/429810/how-to-effectively-unit-test-code-with-lots-of-database-dependencies
[14] https://medium.com/trendyol-tech/how-to-test-database-queries-and-more-with-node-js-2f02b08707a7
[15] https://pretius.com/blog/testcontainers-liquibase
[16] https://www.reddit.com/r/ExperiencedDevs/comments/1g71tk1/unit_testing_and_databases/
[17] https://stackoverflow.com/questions/47439822/unit-testing-with-sqlite3
[18] https://news.ycombinator.com/item?id=42552976
[19] https://stackoverflow.com/questions/79342445/mock-sqlite3-using-jest
[20] https://www.reddit.com/r/learnpython/comments/9h3f5h/how_to_mock_an_sql_database_in_python/
[21] https://www.startearly.ai/post/javascript-unit-testing-guide
[22] https://blog.avenuecode.com/how-to-build-unit-tests-using-jest
[23] https://stackoverflow.com/questions/72698145/postgres-jsonb-not-compatible-with-sqlite-testing-environment
[24] https://www.dustinmartin.net/mock-services-with-mountebank/
[25] https://pypi.org/project/sqlalchemy-json/
[26] https://pythonhosted.org/cubes/backends/sql.html
[27] https://www.reddit.com/r/node/comments/1bi0ufv/different_strategies_for_testing_interaction_with/

---

## Implementation: SQLAlchemy `with_variant`

Our project uses the SQLAlchemy ORM variant approach (option 3 above):

```python
from sqlalchemy import Column, JSON
from sqlalchemy.dialects.postgresql import JSONB

# JSONB for PostgreSQL (production), JSON for SQLite (testing)
results_json = Column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
```

### Files Using This Pattern

- `backend/src/models/analysis_result.py` - `results_json`
- `backend/src/models/pipeline.py` - `nodes_json`, `edges_json`, `validation_errors`
- `backend/src/models/pipeline_history.py` - `nodes_json`, `edges_json`
- `backend/src/models/configuration.py` - `value_json`

### Migrations

Alembic migrations continue to use `postgresql.JSONB` directly since they run against the production PostgreSQL database.

### Future Considerations

For integration tests requiring full JSONB functionality (GIN indexes, containment operators like `@>`, `?`), consider:
- Docker-based PostgreSQL test containers (testcontainers-python)
- Separate integration test suite for JSONB-specific features
- CI pipeline with real PostgreSQL instance
