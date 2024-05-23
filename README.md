# Low Latency Engine

The Low Latency Engine (LLE) is a guide to help you build a real-time data processing pipeline using Tinybird. The guide is divided into three main sections:

* The first section is focused on the problem statement.
* The second section is focused on the data model.
* The third section is focused on the queries/endpoints.

## 1. Problem Statement

### Problem Statement

You are working for a hotel booking platform and you have been tasked with building a real-time data processing pipeline to detect long term discounts and at the same potential fraudsters. The platform generates many events such as searches and bookings per second, and you need to process these events and get a response in real time (less than a second). In doing so, you will be able to offer appropiate discounts to users who are likely to book a property for an extended period of time, and flag potential fraudsters in real-time. 

### Technical Challenges and potential solutions using Tinybird

Low latency use cases could be challenging because it entails two main problems: 

* processing the data in real-time, and
* providing a response in real-time.

The first problem consists of processing the data as soon as it arrives. ClickHouse is really good at ingesting data and transforming it at the same time. [It achieves this thanks to materialized views](https://www.tinybird.co/docs/guides/publish/master-materialized-views), which are precomputed tables that are updated in real-time as new data arrives. 

The second problem consists of providing a response in real-time. Tinybird endpoints will make it possible to query the data in real-time but we would need to structure the data based on the queries we want to run. Each of [our use cases will tell us how to order and configure our engine to provide the best possible response time](https://www.tinybird.co/blog-posts/thinking-in-tinybird). The toolkit that we would use would be adjusting our data types, sorting keys, partitioning and index granularity.

### Use cases

#### Long term discounts

Your platform wants to offer long term visit discounts to users who are likely to book a property for an extended period of time. So if an user that is searching for a booking fulfills at least 5 of the following conditions, he or she will be eligible for a long term discount:

* 3 events of the same `user_id` in less than an hour
* the duration of the booking search (`end_date` - `start_date`) more than 2 weeks
* the `price` is more than 300
* country in `['FR', 'PT', 'IT', 'ES']`
* `property_type` in `['house', 'apartment']`
* `has_wifi` is True
* `has_parking` is True
* `are_pets_allowed` is True

In addition, the query time should be less than 700 ms. The discount should be offered to the user in real-time, before he or she completes the booking.

#### Fraud detection

If an user fulfills at least 7 of the following conditions, he or she will be flagged as a potential fraudster:

* 3 transactions in less than an hour (`event_type` is `booking`)
* each transaction `price` is more than 1000
* the aggegated `price` of the 3 transactions is more than 5000
* 3 different `device` in less than an hour
* 3 different `browser` in less than an hour
* 3 different os in less than an hour
* 3 different `user_location` in less than an hour
* 3 different `card_id` in less than an hour

In addition, the query time should be less than 500 ms. The user should be flagged as a potential fraudster in real-time. 

## 2. Data Model

### Ingestion

As stated above, in our booking platform we are generating many events per second. In real life, these events could being captured using Kafka or Tinybird's events API. We could mock the ingestion using Tinybird's Events API with [Mockingbird](https://mockingbird.tinybird.co/) based on [this json schema](/datasources/booking_events.json). 

### Data Source

* `event_id` (Int32): Unique identifier for each event.
* `event_time` (DateTime): Timestamp of the event.
* `event_type` (String): Type of event (e.g., search, booking, cancellation).
* `device` (String): Device used for the event (e.g., mobile, desktop).
* `browser` (String): Browser used during the event.
* `os` (String): Operating system used during the event.
* `user_id` (Int32): Identifier for the user involved in the event.
* `user_location` (String): Location of the user at the time of the event.
* `booking_city` (String): City of the booking.
* `booking_country` (String): Country of the booking.
* `start_datetime` (Date): Check-in date for the booking.
* `end_datetime` (Date): Check-out date for the booking.
* `price` (Float64): Price per night of the booking.
* `currency` (String): Currency used for the booking.
* `product_id` (Int32): Identifier for the product.
* `property_type` (String): Type of property (e.g., hotel, apartment).
* `are_pets_allowed` (Int8): Indicates if pets are allowed (0 for no, 1 for yes).
* `has_wifi` (Int8): Indicates if the property has Wi-Fi (0 for no, 1 for yes).
* `has_parking` (Int8): Indicates if the property has parking (0 for no, 1 for yes).
* `card_id` (Int32): Identifier for the card used for booking.
* `card_issuer` (String): Issuer of the card used.

### Materialized Views

#### Data Preparation

There are some data preparation steps that will be common to both use cases:

* converting dates instead of timestamps,
* calculating the duration of the booking,
* normalizing prices using just one currencty (e.g., USD),
* removing unnecessary columns (e.g., `event_id`, `product_id`, `currency`, etc.),
* applying a type modifier such as low cardinality to strings with fewer categories (e.g. `event_type`, `device`, `browser`, etc.).

#### Partitioning and index granularity

* The data will be partitioned by `event_time` but reducing the partition size. Small partitions will be merged faster so queries will be faster. Notice that small partition sizes could break the ingestion due too many parts errors so we should be mindful of this issue and adjust the partition size accordingly. In this respect, we have chosen to partition by weeks, a good time range granularity balancing:

```
ENGINE_PARTITION_KEY "toDayOfWeek(event_time)"
```

* The data source will be indexed by `user_id` and `event_type`. But for each use case we will use other indexes to adjust to the particular filtering conditions.

* Finally, we could tweak our index granularity to reduce the amount of data you read. [ClickHouse by default sets 8192 rows per each granule](https://clickhouse.com/docs/en/optimize/skipping-indexes), so we could have less number of rows (e.g. 2048). We would need to play with the size since a very small size impacts the inserts and other kind of queries (e.g. range). 

```
SETTINGS "index_granularity=2048"
```

#### Long term discounts

In order to precalculate the conditions for the long term discounts, we will create a materialized view that will filter the events that fulfill the conditions for the long term discounts:
* first, we will prepare the conditions that need to be checked,
* then, we will filter the users that fulfill at least 5 conditions,
* finally, we will filter the users that have more than 3 searches.

```sql
NODE prepare_conditions_checked
SQL >

    SELECT 
      user_id,
      event_time,
      if(booking_duration > 14, 1, 0) as is_duration_checked,
      if(price_in_usd > 300, 1, 0) as is_price_checked,
      if(booking_country in ('FR', 'PT', 'IT', 'ES'), 1, 0) as is_country_checked,
      if(property_type in ('house', 'apartment'), 1, 0) as is_property_type_checked,
      has_wifi as is_wifi_checked,
      has_parking as is_parking_checked,
      are_pets_allowed as is_pets_allowed_checked
    FROM booking_events_mv
    WHERE event_type = 'search'
    AND event_time >= now() - INTERVAL 1 HOUR

NODE get_users_fulfilling_5_conditions
SQL >

    WITH (is_duration_checked+is_price_checked+is_country_checked+is_property_type_checked+is_wifi_checked+is_parking_checked+is_pets_allowed_checked) as discount_index
    SELECT 
      user_id,
      toStartOfHour(event_time) as hour,
      count() as search_count
    FROM prepare_conditions_checked
    WHERE discount_index >= 5
    GROUP BY user_id, hour

NODE get_users_with_more_than_3_searches
SQL >

    SELECT DISTINCT
        user_id,
        hour
    FROM get_users_fulfilling_5_conditions
    WHERE search_count > 3
    ORDER BY search_count DESC

TYPE materialized
DATASOURCE get_users_with_more_than_3_searches_mv

```

This materialized view is ready to be queried in real-time to offer the long term discount to the users that fulfill the conditions.

#### Fraud detection

TBD

## 3. Queries/Endpoints

TBD
