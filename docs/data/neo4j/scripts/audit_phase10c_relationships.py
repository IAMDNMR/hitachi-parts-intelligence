#!/usr/bin/env python3
"""Live Neo4j relationship inventory audit for Phase 10C planning."""
import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv('backend/.env')
d = GraphDatabase.driver(os.environ['NEO4J_URI'], auth=(os.environ['NEO4J_USER'], os.environ['NEO4J_PASSWORD']))

with d.session() as s:
    print('=== RELATIONSHIP INVENTORY ===')
    rels = s.run('CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType ORDER BY relationshipType').value()
    for r in rels:
        rows = s.run(
            f'MATCH (a)-[:{r}]->(b) RETURN labels(a)[0] as from_lbl, labels(b)[0] as to_lbl, count(*) as cnt ORDER BY cnt DESC LIMIT 3'
        ).data()
        for row in rows:
            print(f'{r}: {row["from_lbl"]} -> {row["to_lbl"]} ({row["cnt"]})')

    print()
    print('=== SUPPLIER NODES ===')
    sup = s.run('MATCH (s:Supplier) RETURN s.supplier_number as num, s.name as name, s.city as city, s.country as country, s.synthetic as syn LIMIT 5').data()
    for r in sup:
        print(r)
    total = s.run('MATCH (s:Supplier) RETURN count(s) as c').single()['c']
    print(f'Total Supplier nodes: {total}')

    print()
    print('=== CITY/COUNTRY NODES ===')
    city_c = s.run('MATCH (c:City) RETURN count(c) as c').single()['c']
    country_c = s.run('MATCH (c:Country) RETURN count(c) as c').single()['c']
    print(f'City nodes: {city_c}, Country nodes: {country_c}')

    print()
    print('=== ORDER STATUS DISTRIBUTION ===')
    orders = s.run('MATCH (o:Order) WHERE o.testRunId IS NULL RETURN o.status as status, count(o) as cnt ORDER BY cnt DESC').data()
    for r in orders:
        print(r)

    print()
    print('=== SHIPMENT STATUS ===')
    ships = s.run('MATCH (s:Shipment) WHERE s.testRunId IS NULL RETURN s.status as status, count(s) as cnt ORDER BY cnt DESC').data()
    for r in ships:
        print(r)

    print()
    print('=== DEALER LOCATED_IN CITY SAMPLE ===')
    dloc = s.run('MATCH (d:DealerBranch)-[:LOCATED_IN]->(c:City) RETURN count(d) as cnt').single()
    print(f'DealerBranch-[:LOCATED_IN]->City: {dloc["cnt"]}')

    print()
    print('=== SUPPLIER LOCATED_IN CITY SAMPLE ===')
    sloc = s.run('MATCH (s:Supplier)-[:LOCATED_IN]->(c:City) RETURN count(s) as cnt').single()
    print(f'Supplier-[:LOCATED_IN]->City: {sloc["cnt"]}')

d.close()
print('DONE')
