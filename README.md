# Low Latency Engine

The Low Latency Engine (LLE) is a guide to help you build a real-time data processing pipeline using Tinybird. The guide is divided into three main sections:

* The first section is focused on the problem statement and use cases.
* The second section is focused on the data model.
* The third section is focused on the queries/endpoints.

## 1. Problem Statement and Use Cases

### Problem Statement

You are working for a hotel booking platform and you have been tasked with building a real-time data processing pipeline on top of [Tinybird](https://www.tinybird.co/) to detect long term discounts and potential fraudsters. The data is being ingested [using Tinybird's Events API](https://www.tinybird.co/docs/guides/ingest/ingest-from-the-events-api). The data source contains information about hotel booking events, such as the event type (e.g., search, booking, cancellation), the device used for the event (e.g., mobile, desktop), the browser used during the event, the operating system used during the event, the user involved in the event, the location of the user at the time of the event, the country of the booking, the check-in and check-out dates for the booking, the price of the booking, the currency used for the booking, the type of property (e.g., hotel, apartment), whether pets are allowed, whether the property has Wi-Fi, whether the property has parking, the card used for the booking, the issuer of the card used, whether the booking is confirmed, and whether the booking was cancelled. 

### Use cases

#### Long term discounts

Your platform wants to offer long term visit discounts to users who are likely to book a property for an extended period of time. So if an user fulfills at least 5 of the following conditions, he or she will be eligible for a long term discount:

* the `event_type` is `search`
* 3 events of the same `user_id` in less than an hour
* the duration of the booking search (`end_date` - `start_date`) more than 2 weeks
* the `price` is more than 1000
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

### Ingestion

The data is being ingested using Tinybird's Events API using [Mockingbird](https://mockingbird.tinybird.co/) based on [json this schema](/datasources/booking_events.json). In this case, we are generating 5 events per second.

### Materialized Views

#### Data Preparation

There are some data preparation steps that will be common to both use cases:

* converting dates instead of timestamps,
* calculating the duration of the booking,
* normalizing prices using just one currencty (e.g., USD),
* removing unnecessary columns (e.g., `event_id`, `product_id`, `currency`, etc.),
* applying a type modifier such as low cardinality to strings with fewer categories (e.g. `event_type`, `device`, `browser`, etc.).

#### Long term discounts

TBD

#### Fraud detection

TBD

## 3. Queries/Endpoints

TBD
