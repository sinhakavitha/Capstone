# Module 1 — Data Pipeline

This scrapes book data from books.toscrape.com, cleans it up, converts the
price to INR, and loads everything into a small SQLite database that I then
query with SQL and pandas. Everything's in `scraper.ipynb`.

## Getting it running

```
pip install requests beautifulsoup4 pandas jupyter nbformat nbconvert
jupyter nbconvert --to notebook --execute --inplace scraper.ipynb
```

(or just open the notebook in Jupyter and run all cells).

I went with 5 categories — Travel, Mystery, Historical Fiction, Sequential
Art, Classics — which comes out to 163 books, comfortably past the 60-book
minimum. One thing to watch for: I originally had the table-creation step
use `CREATE TABLE IF NOT EXISTS`, and re-running the notebook against an
existing `books.db` quietly doubled every row. Now the notebook drops and
recreates both tables at the start of every run, so it's safe to re-run as
many times as you want.

## Cleaning the scraped fields

- `price` comes back as something like `£51.77` — I strip the symbol and
  cast to float for `price_gbp`.
- `star_rating` is a word ("Three", "Five", etc.) — mapped through a small
  dict to an int 1–5 for `rating`.
- `availability` is free text — I just check whether it contains "in
  stock" to get a boolean `in_stock`.

For rows that don't parse cleanly, I didn't want the whole pipeline to die
on one bad row, so: numeric fields (`price_gbp`, `rating`) fall back to the
median of whatever did parse, and rows with a blank title or unrecognizable
availability text just get dropped — I'd rather lose a row than fabricate a
title or a stock status. In practice the live data was clean and neither
path ever triggered, but the handling is there.

## Currency

Using the fixed rate the assignment specifies: **1 GBP = 105.50 INR**. It's
a made-up constant for this exercise, not a real exchange rate, so no API
call or lookup involved — just `price_inr = price_gbp * 105.50`.

## Database schema

Two tables, straightforward one-to-many via `category_id`:

```sql
categories(category_id INTEGER PRIMARY KEY, category_name TEXT UNIQUE)

books(book_id INTEGER PRIMARY KEY, title TEXT, price_gbp REAL,
      price_inr REAL, rating INTEGER, in_stock INTEGER,
      category_id INTEGER REFERENCES categories(category_id))
```

## Queries

Five queries in the notebook, each printed with its output:

1. Priciest in-stock books in INR — `WHERE` + `ORDER BY` + `LIMIT`
2. Which ratings actually show up in the data — `DISTINCT`
3. Books rated 4 or 5 stars — `IN`
4. Books priced between £20 and £30 — `BETWEEN`
5. Top 10 rated books alongside their category name — `JOIN`

All five get read back into a DataFrame with `pd.read_sql`. For the join
query, I also rebuilt the same result by hand with `pd.merge` on the raw
DataFrames (no SQL involved) and checked it matches the SQL output exactly
— it does.
