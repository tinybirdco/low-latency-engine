# Low Latency Engine

The Low Latency Engine (LLE) is a guide to help you build a real-time data processing pipeline using Tinybird. The guide is divided into two main sections:

* The first section is focused on the problem statement.
* The second section is focused on the data model.

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

Your platform wants to offer long term visit discounts to users who are likely to book a property for an extended period of time. So if an user that is searching for a booking at the same location fulfills at least 5 of the following conditions, he or she will be eligible for a long term discount:

* the duration of the booking search (`end_date` - `start_date`) more than 2 months
* the `price` is more than 300
* country in `['FR', 'PT', 'IT', 'ES']`
* `property_type` in `['house', 'apartment']`
* `has_wifi` is True
* `has_parking` is True
* `are_pets_allowed` is True

In addition, the query time should be less than 700 ms. The discount should be offered to the user in real-time, before he or she completes the booking. Finally, the parameters in this query should be dynamic in part to allow our marketing team to adjust the conditions for the long term discounts.

#### Fraud detection

If an user performs 3 transactions in less than 5 minutes (`event_type` is `booking`) and fulfills at least 3 of the following conditions, he or she will be flagged as a potential fraudster:

* each transaction `price` is more than 300
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

### Data Preparation

There are some data preparation steps that will be common to both use cases:

* converting dates instead of timestamps,
* calculating the duration of the booking,
* normalizing prices using just one currencty (e.g., USD),
* removing unnecessary columns (e.g., `event_id`, `product_id`, `currency`, etc.),
* applying a type modifier such as low cardinality to strings with fewer categories (e.g. `event_type`, `device`, `browser`, etc.).

### Partitioning and index granularity

* The data will be partitioned by `event_time` but reducing the partition size. Small partitions will be merged faster so queries will be faster. Notice that small partition sizes could break the ingestion due too many parts errors so we should be mindful of this issue and adjust the partition size accordingly. Partitioning keys can be set in [Tinybird's data source](https://www.tinybird.co/docs/version-control/datafiles#data-source) as follows:

```
ENGINE_PARTITION_KEY "toHour(event_time)"
```

* The data source will be indexed by `user_id` and `event_type`. But for each use case we will use other indexes in every materialized view to adjust to the particular filtering conditions.

* Finally, we could tweak our index granularity to reduce the amount of data you read. [ClickHouse by default sets 8192 rows per each granule](https://clickhouse.com/docs/en/optimize/skipping-indexes), so we could have less number of rows (e.g. 2048). We would need to play with the size since a very small size impacts the inserts and other kind of queries (e.g. range). Index granularity could be set as follows in [Tinybird's data source](https://www.tinybird.co/docs/version-control/datafiles#data-source):

```
SETTINGS "index_granularity=2048"
```

### Long term discounts

In order to precalculate the conditions for the long term discounts, we will create a materialized view that will filter the events that fulfill the conditions for the long term discounts:
* first, we will prepare the conditions that need to be checked building a discount matrix,
* then, we will filter the users that fulfill the discount value set by our analysts,
* finally, we will get the unique customer ids to send them the discount.

```sql
TOKEN "long_term_discount_endpoint_read" READ

NODE discount_matrix
SQL >

    %
    SELECT 
      user_id,
      if(booking_duration >= {{Int16(months, 2)}}*30, 1, 0) as duration_value,
      if(price_in_usd > {{Int16(usd, 300)}}, 1, 0) as price_value,
      if(booking_country in {{Array(countries, 'String', default='FR,PT')}}, 1, 0) as countries_value,
      if(property_type in {{Array(countries, 'String', default='house,apartment')}}, 1, 0) as property_value,
      if(has_wifi = {{Int16(wifi_flag, 1)}}, 1, 0) as wifi_value,
      if(has_parking = {{Int16(parking_flag, 1)}}, 1, 0) as parking_value,
      if(are_pets_allowed = {{Int16(pets_flag, 1)}}, 1, 0) as pets_value
    FROM
      booking_events_mv
    WHERE
      event_type = 'search'
      and event_time >= toTimezone(now(), 'Europe/Berlin') - interval 10 second

NODE filter_by_discount_index
SQL >

    %
    WITH (
      duration_value+price_value+countries_value+property_value+wifi_value+parking_value+pets_value
    ) as discount_index
    SELECT
      user_id,
      discount_index
    FROM discount_matrix
    WHERE discount_index >= {{Int16(discount, 5)}}
    ORDER BY discount_index DESC

NODE get_unique_customers
SQL >

    SELECT DISTINCT user_id FROM filter_by_discount_index
```

An example of an API endpoint call would be:

```
https://api.tinybird.co/v0/pipes/long_term_discount.json?discount=5&months=2&usd=300&countries=house%2Capartment&wifi_flag=1&parking_flag=1&pets_flag=1
```

And the results would be:

```json
{
  "meta": [
    {
      "name": "user_id",
      "type": "Int32"
    }
  ],
  "data": [
    {
      "user_id": 189012
    },
    {
      "user_id": 345678
    },
    {
      "user_id": 201234
    },
    {
      "user_id": 678901
    }
  ],
  "rows": 4,
  "statistics": {
    "elapsed": 0.018713724,
    "rows_read": 65,
    "bytes_read": 2065
  }
}
```

18 ms! Not bad.

### Fraud detection

For the fraud detection use case, we will build a non dynamic endpoint that will filter the users that fulfill the conditions for the potential fraudsters:
* first, we will group the events by user and count the number of events for each user,
* then, we will build a fraud detection matrix with the conditions that need to be checked,
* finally, we will filter the users that fulfill the fraud detection value set by our analysts.


```sql
TOKEN "fraud_detection_endpoint_read" READ

NODE booking_events_last_5_minutes
SQL >

    SELECT
        user_id,
        event_time,
        device,
        browser,
        os,
        user_location,
        card_id,
        price_in_usd
    FROM
        booking_events_mv
    WHERE
        event_type = 'booking'
    AND event_time > toTimezone(now(), 'Europe/Berlin') - INTERVAL 5 MINUTE

NODE group_and_count_by_user
SQL >

    SELECT
        user_id,
        count() AS booking_count,
        count(DISTINCT device) AS device_count,
        count(DISTINCT browser) AS browser_count,
        count(DISTINCT os) AS os_count,
        count(DISTINCT user_location) AS user_location_count,
        count(DISTINCT card_id) AS card_id_count,
        sum(if(price_in_usd > 300, 1, 0)) AS high_price_count
    FROM
        booking_events_last_5_minutes
    GROUP BY
        user_id
    HAVING
        booking_count >= 5

NODE fraud_detection_matrix
SQL >

    SELECT
        user_id,
        if(device_count > 3, 1, 0) as device_value,
        if(browser_count > 3, 1, 0) as browser_value,
        if(os_count > 3, 1, 0) as os_value,
        if(user_location_count > 3, 1, 0) as user_location_value,
        if(card_id_count > 3, 1, 0) as card_id_value,
        if(high_price_count > 3, 1, 0) as price_in_usd_value
    FROM
        group_and_count_by_user

NODE filter_by_fraud_detection_index
SQL >

    %
    WITH (
      device_value+browser_value+os_value+user_location_value+card_id_value+price_in_usd_value
    ) as fraud_detection_index
    SELECT
      user_id,
      fraud_detection_index
    FROM fraud_detection_matrix
    WHERE fraud_detection_index >= 3
    ORDER BY fraud_detection_index DESC

NODE get_potential_fraudsters
SQL >

    SELECT DISTINCT user_id FROM filter_by_fraud_detection_index
```

In this use case because the conditions are not dynamic, we could have built a materialized view to precalculate the fraud detection matrix and filter the users that fulfill the conditions for the potential fraudsters. 

An example of an API endpoint call would be:

```
https://api.tinybird.co/v0/pipes/fraud_detection.json
```

And the results would be:

```json
{
 "meta": [
    {
      "name": "user_id",
      "type": "Int32"
    }
  ],
  "data": [
    {
      "user_id": 234567
    }
  ],
  "rows": 1,
  "rows_before_limit_at_least": 1,
  "statistics": {
    "elapsed": 0.027963912,
    "rows_read": 1035,
    "bytes_read": 25875
  }
}
```

Same as the other use case, 28 ms! Not bad at all.
