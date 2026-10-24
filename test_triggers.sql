
PRAGMA foreign_keys = ON;

-- Test users
INSERT INTO users (user_id, name, email, password_hash, role)
VALUES
    (1, 'Test Caterer', 'caterer@test.com', 'hash1', 'caterer'),
    (2, 'Test Recipient', 'recipient@test.com', 'hash2', 'recipient'),
    (3, 'Second Caterer', 'caterer2@test.com', 'hash3', 'caterer');

-- Test food listings
INSERT INTO food_listings (
    food_id, caterer_id, food_name, food_description,
    quantity, unit, prepared_date, pickup_deadline
)
VALUES
    (101, 1, 'Vegetable Rice', 'Fresh vegetable rice',
     20, 'portions', '2026-10-17T10:00:00',
     '2026-10-17T14:00:00'),
    (102, 3, 'Bread Rolls', 'Fresh bread rolls',
     10, 'pieces', '2026-10-17T10:00:00',
     '2026-10-17T14:00:00');

-- TEST 1: Recipient requests another caterer's listing.
-- Expected: SUCCESS
INSERT INTO listing_requests (food_id, recipient_id)
VALUES (101, 2);

SELECT 'TEST 1: recipient request succeeded' AS result;

-- TEST 2: Caterer requests their own listing.
-- Expected: FAILURE — own-listing trigger
INSERT INTO listing_requests (food_id, recipient_id)
VALUES (101, 1);

-- TEST 3: Caterer requests another caterer's listing.
-- Expected: FAILURE — recipient-role trigger
INSERT INTO listing_requests (food_id, recipient_id)
VALUES (102, 1);

