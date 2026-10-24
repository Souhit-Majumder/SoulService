PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('recipient', 'caterer', 'admin')),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS food_listings (
    food_id INTEGER PRIMARY KEY,
    caterer_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    food_name TEXT NOT NULL,
    food_description TEXT NOT NULL,
    pickup_location TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit TEXT NOT NULL,
    prepared_date TEXT NOT NULL,
    pickup_deadline TEXT NOT NULL CHECK (pickup_deadline > prepared_date),
    status TEXT NOT NULL DEFAULT 'available' 
    CHECK (status IN ('available', 'reserved', 'picked_up', 'cancelled')),    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS listing_requests (
    request_id INTEGER PRIMARY KEY,
    food_id INTEGER NOT NULL REFERENCES food_listings(food_id) ON DELETE RESTRICT,
    recipient_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'pending' 
    CHECK (status IN ('pending', 'accepted', 'rejected', 'cancelled', 'picked_up')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS listing_dietary_infos (
    food_id INTEGER NOT NULL
        REFERENCES food_listings(food_id) ON DELETE CASCADE,
    dietary_info TEXT NOT NULL,
    PRIMARY KEY (food_id, dietary_info)
);

CREATE TABLE IF NOT EXISTS listing_allergens (
    food_id INTEGER NOT NULL
        REFERENCES food_listings(food_id) ON DELETE CASCADE,
    allergen TEXT NOT NULL,
    PRIMARY KEY (food_id, allergen)
);


CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_request
ON listing_requests (food_id, recipient_id)
WHERE status IN ('pending', 'accepted');

CREATE UNIQUE INDEX IF NOT EXISTS idx_one_accepted_request_per_listing
ON listing_requests (food_id)
WHERE status = 'accepted';



CREATE TRIGGER IF NOT EXISTS tr_only_recipents_can_request
BEFORE INSERT ON listing_requests
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Only recipients can request food listings')
    FROM users
    WHERE user_id = NEW.recipient_id AND role != 'recipient';
END;

CREATE TRIGGER IF NOT EXISTS tr_user_cannot_request_own_listing
BEFORE INSERT ON listing_requests
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'A user cannot request their own food listing')
    FROM users
    WHERE user_id = NEW.recipient_id 
        AND user_id = (SELECT caterer_id FROM food_listings WHERE food_id = NEW.food_id);
END;

CREATE TRIGGER IF NOT EXISTS tr_update_food_status_on_request_accept
BEFORE UPDATE OF status ON listing_requests
FOR EACH ROW
WHEN NEW.status = 'accepted'
BEGIN
    SELECT RAISE(ABORT, 'Cannot accept request - listing is unavailable or expired')
    WHERE EXISTS (
        SELECT 1
        FROM food_listings
        WHERE food_id = NEW.food_id
          AND (
              status != 'available'
              OR pickup_deadline <= datetime('now')
          )
    );
END;
    
CREATE TRIGGER IF NOT EXISTS tr_update_food_status_on_reservation
AFTER UPDATE OF status ON listing_requests
FOR EACH ROW
WHEN NEW.status = 'accepted'
BEGIN
    UPDATE food_listings
    SET status = 'reserved'
    WHERE food_id = NEW.food_id;
END;

CREATE TRIGGER IF NOT EXISTS tr_reopen_listing_on_request_cancel
AFTER UPDATE OF status ON listing_requests
FOR EACH ROW
WHEN OLD.status = 'accepted'
     AND NEW.status = 'cancelled'
BEGIN
    UPDATE food_listings
    SET status = 'available'
    WHERE food_id = NEW.food_id
      AND status = 'reserved'
      AND pickup_deadline > datetime('now');
END;

CREATE TRIGGER IF NOT EXISTS tr_validate_pickup
BEFORE UPDATE OF status ON listing_requests
FOR EACH ROW
WHEN NEW.status = 'picked_up'
BEGIN
    SELECT RAISE(ABORT, 'Only an accepted request can be picked up')
    WHERE OLD.status != 'accepted';

    SELECT RAISE(ABORT, 'Listing is not reserved or pickup deadline has passed')
    WHERE NOT EXISTS (
        SELECT 1
        FROM food_listings
        WHERE food_id = NEW.food_id
          AND status = 'reserved'
          AND pickup_deadline > datetime('now')
    );
END;

CREATE TRIGGER IF NOT EXISTS tr_update_food_status_on_pickup
AFTER UPDATE OF status ON listing_requests
FOR EACH ROW
WHEN NEW.status = 'picked_up'
BEGIN
    UPDATE food_listings
    SET status = 'picked_up'
    WHERE food_id = NEW.food_id;
END;