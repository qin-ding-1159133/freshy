DROP DATABASE IF EXISTS fresh_harvest_delivery_db;
CREATE DATABASE IF NOT EXISTS fresh_harvest_delivery_db;
USE fresh_harvest_delivery_db;

CREATE TABLE roles (
    role_id INT AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(255) NOT NULL
);
INSERT INTO roles (role_name) VALUES ('National Manager'), ('Local Manager'), ('Staff'),('Customer'),('Account');

create table daily_fresh_subscriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fresh_date date not null
);

insert into daily_fresh_subscriptions values
(1,'2024-05-16'),
(2,'2024-05-17');


CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    password_hashed VARCHAR(255) NOT NULL,
    role_id INT,
	status ENUM('Active', 'Inactive') NOT NULL,
    constraint FOREIGN KEY (role_id) REFERENCES roles(role_id)
);
INSERT INTO users (user_id,username,password_hashed,role_id, `status`) VALUES 
(1,'sam', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','1', 'Active'),
(2,'jim', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','2', 'Active'),
(3,'john', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','3', 'Active'),
(4,'jane', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','3', 'Active'),
(5,'david', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','2', 'Active'),
(6,'emily', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','3', 'Active'),
(7,'ava', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','3', 'Active'),
(8,'mia', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','2', 'Active'),
(9,'sophia', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','3', 'Active'),
(10,'edr','c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','3', 'Active'),
(11,'buel','c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','2', 'Active'),
(12,'gree','c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','3', 'Active'),
(13,'park','c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','3', 'Active'),
(14,'yeen','c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','2', 'Active'),
(15,'cryan','c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','3', 'Active'),
(16,'lee','c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','3', 'Active'),



(17,'sarah','c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','4', 'Active'),
(18,'jessica', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','4', 'Active'),
(19,'olivia', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','4', 'Active'),
(20,'noah', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','4', 'Active'),
(21,'isabella', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','4', 'Active'),
(22,'alison', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','4', 'Active'),
(23,'madison', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','4', 'Active'),
(24,'mod', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','4', 'Active'),
(25,'hannah', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','4', 'Active'),
(26,'abigail', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','4', 'Active'),



(27,'cornwallparkcafe', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','5', 'Active'),
(28,'cafeberlin', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','5', 'Active'),
(29,'freshoneltd', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','5', 'Active'),
(30,'brewhaven', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','5', 'Active'),
(31,'thebeanery', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','5', 'Active'),
(32,'javajunction', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','5', 'Active'),
(33,'cozycornercoffee','c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','5', 'Active'),
(34,'sunrisesipscafe', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','5', 'Active'),
(35,'greenleafgrind', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','5', 'Active'),
(36,'mochamagiccafe', 'c77fe2e1d71e76f4d88099f5de56fb3411416b393ddb09c880d9b3c7850b1c5e','5', 'Active');



CREATE TABLE depots (
   depot_id INT AUTO_INCREMENT PRIMARY KEY,
   location text not null
);
INSERT INTO depots (location) VALUES ('Auckland'), ('Christchurch'), ('Wellington'),('Hamilton'),('Invercargill');
CREATE TABLE customers (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(50),
    given_name VARCHAR(255) NOT NULL,
    family_name VARCHAR(255) NOT NULL,
	email VARCHAR(255) NOT NULL,
    customer_address TEXT not null,
    city int not null,
    phone_number VARCHAR(20),
    balance DECIMAL(10,2) NOT NULL,
    pic VARCHAR(255),
    constraint FOREIGN KEY (user_id) REFERENCES users(user_id),
	constraint FOREIGN KEY (city) REFERENCES depots(depot_id)
);
INSERT INTO customers (user_id, title,given_name,family_name,email,customer_address,city,phone_number,balance,pic) values
(17,'Ms.','Sarah','Kim','sarah@outlook.com','3 Wiri Road',1,'031234567',20.00,'app/static/assets/img/avatar-06.png'),
(18,'Ms.','Jessica','Lau','jessica@outlook.com','3 Wiri Road',1,'031254125',0.00,'app/static/assets/img/avatar-10.png'),
(19,'Ms.','Olivia','Smith','olivia@outlook.com','10 Elm Street',2,'032345678',50.00,'app/static/assets/img/avatar-13.png'),
(20,'Mr.','Noah','Chen','noah@outlook.com','45 Maple Avenue',2,'032365123',30.00,'app/static/assets/img/avatar-14.png'),
(21,'Ms.','Isabella','Lee','isabella@outlook.com','78 Pine Road',3,'032356789',15.00,'app/static/assets/img/avatar-13.png'),
(22,'Ms.','Alison','Ng','ava@outlook.com','22 Oak Lane',3,'032377451',10.00,'app/static/assets/img/avatar-13.png'),
(23,'Ms.','Madison','Brown','madison@outlook.com','90 Cedar Street',4,'032389765',40.00,'app/static/assets/img/avatar-13.png'),
(24,'Ms.','Mod','Wong','mia@outlook.com','12 Birch Avenue',4,'032398712',25.00,'app/static/assets/img/avatar-13.png'),
(25,'Ms.','Hannah','Nguyen','hannah@outlook.com','34 Willow Road',5,'032412367',60.00,'app/static/assets/img/avatar-13.png'),
(26,'Ms.','Abigail','Olsen','abigail@outlook.com','76 Chestnut Drive',5,'032432165',0.00,'app/static/assets/img/avatar-13.png');

create table units ( 
     unit_id INT AUTO_INCREMENT PRIMARY KEY,
     unit_name VARCHAR(255) NOT NULL,
     status ENUM('Active', 'Inactive') NOT NULL
     
);
insert into units values 
(1,'kg','Active'),
(2,'each','Active'),
(3,'250g','Active'),
(4,'pc','Active'),
(5,'punnet','Active'),
(6,'pack','Active'),
(7,'small','Active'),
(8,'medium','Active'),
(9,'large','Active'),
(10,'dozen','Active'),
(11,'bunch','Active'),
(12,'500g','Active'),
(13,'bag','Active');

CREATE TABLE accounts (
    account_id INT AUTO_INCREMENT PRIMARY KEY,
	user_id INT not null,
    account_name VARCHAR(255) NOT NULL,
    account_address text NOT NULL,
    city int not null,
	email VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20),
	pic VARCHAR(255),
    credit_limit_monthly DECIMAL(10,2) NOT NULL,
	balance DECIMAL(10,2) NOT NULL,
    constraint FOREIGN KEY (user_id) REFERENCES users(user_id),
	constraint FOREIGN KEY (city) REFERENCES depots(depot_id)

);
INSERT INTO accounts (account_id,user_id, account_name,account_address,city, email,phone_number,pic, credit_limit_monthly, balance) values
(1,27,'Cornwall Park Cafe','Cornwall Park Pohutakawa Drive, Epsom, Auckland',1,'nikaocafe@outlook.com','0218521456','app/static/assets/img/account-icon.jpg',1000.00,-211.97),
(2,28,'Cafe Berlin','9C Normans Road',1,'cafeberlin@outlook.com','0288521777','app/static/assets/img/account-icon.jpg',500.00,-91.00),
(3,29,'Fresh One Ltd','123 Garden Road, Christchurch',2,'freshoneltd@outlook.com','0238521456','app/static/assets/img/account-icon.jpg',1000.00,0.00),
(4,30,'Brew Haven','45 Lake Street, Christchurch',2,'brewhaven@outlook.com','0218521453','app/static/assets/img/account-icon.jpg',500.00,0.00),
(5,31,'The Beanery','67 Coffee Lane, Wellington',3,'thebeanery@outlook.com','0268521450','app/static/assets/img/account-icon.jpg',800.00,0.00),
(6,32,'Java Junction','89 Espresso Boulevard, Wellington',3,'javajunction@outlook.com','0218521454','app/static/assets/img/account-icon.jpg',1200.00,0.00),
(7,33,'Cozy Corner Coffee','101 Cozy Lane, Hamilton',4,'cozycornercoffee@outlook.com','0228521451','app/static/assets/img/account-icon.jpg',600.00,0.00),
(8,34,'Sunrise Sips Cafe','23 Morning Drive, Hamilton',4,'sunrisesipscafe@outlook.com','0278521456','app/static/assets/img/account-icon.jpg',950.00,0.00),
(9,35,'Green Leaf Grind','89 Natural Street, Invercargill',5,'greenleafgrind@outlook.com','0285685214','app/static/assets/img/account-icon.jpg',700.00,0.00),
(10,36 ,'Mocha Magic Cafe','45 Cocoa Avenue, Invergargill',5,'mochamagiccafe@outlook.com','0218565214','app/static/assets/img/account-icon.jpg',1100.00,0.00);



CREATE TABLE applications (
    application_id INT AUTO_INCREMENT PRIMARY KEY,
    credit_limit_monthly DECIMAL(10,2) NOT NULL,   
    support_doc VARCHAR(255),
    status ENUM ('Pending', 'Approved', 'Declined') NOT NULL,
    applied_by int not null,
    approved_by int ,
    increase_reason VARCHAR(255),
    applied_date DATE,
    decline_reason VARCHAR(255),
	constraint FOREIGN KEY (applied_by) REFERENCES users(user_id)
);


INSERT INTO applications (credit_limit_monthly, support_doc, status, applied_by, approved_by,increase_reason,applied_date,decline_reason) VALUES
(1000.00, '', 'Approved', 12, 2,'','2024-05-16',''),
(500.00, '', 'Approved', 13, 5,'','2024-05-16',''),
(1200.00, '', 'Pending', 10, 1,'','2024-05-16',''),
(800.00, '', 'Declined', 14, 3,'','2024-05-16',''),
(1500.00, '', 'Approved', 11, 4,'','2024-05-16',''),
(750.00, '', 'Approved', 15, 2,'','2024-05-16',''),
(650.00, '', 'Declined', 16, 5,'','2024-05-16',''),
(900.00, '', 'Pending', 17, 1,'','2024-05-16',''),
(1100.00, '', 'Approved', 18, 2,'','2024-05-16',''),
(550.00, '', 'Declined', 19, 3,'','2024-05-16',''),
(1300.00, '', 'Approved', 20, 4,'','2024-05-16',''),
(700.00, '', 'Approved', 21, 2,'','2024-05-16',''),
(450.00, '', 'Declined', 22, 5,'','2024-05-16',''),
(1250.00, '', 'Pending', 23, 1,'','2024-05-16',''),
(950.00, '', 'Approved', 24, 2,'','2024-05-16',''),
(1050.00, '', 'Approved', 25, 3,'','2024-05-16',''),
(1150.00, '', 'Declined', 26, 4,'','2024-05-16',''),
(1350.00, '', 'Approved', 27, 5,'','2024-05-16',''),
(1450.00, '', 'Pending', 28, 1,'','2024-05-16',''),
(1550.00, '', 'Approved', 29, 2,'','2024-05-16','');


CREATE TABLE responsibilities (
   responsibility_id INT AUTO_INCREMENT PRIMARY KEY,
   responsibility_name text not null
);

insert into responsibilities (responsibility_id,responsibility_name) values
(1,'Management'),
(2,'Packing'),
(3,'Delivery');


CREATE TABLE staff (
    staff_id INT AUTO_INCREMENT PRIMARY KEY,
	user_id INT,
    title VARCHAR(50),
    given_name VARCHAR(255) NOT NULL,
    family_name VARCHAR(255) NOT NULL,
	email VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20),
    pic VARCHAR(255),
    responsibility_id int not null,
    depot_id int not null,
    constraint FOREIGN KEY (user_id) REFERENCES users(user_id),
	constraint FOREIGN KEY (responsibility_id) REFERENCES responsibilities(responsibility_id),
	constraint FOREIGN KEY (depot_id) REFERENCES depots(depot_id)
);
INSERT INTO `staff` (staff_id,user_id, title,given_name,family_name,email,phone_number,pic,responsibility_id,depot_id) VALUES 
(1,1,'Mr','Sam','Corren','sam@freshharvest.co.nz','0221356836','app/static/assets/img/avatar-04.png',1,1),
(2,2,'Mr','Jim','Ryn','jim@freshharvest.co.nz','022451235','app/static/assets/img/avatar-07.png',1,1),
(3,3,'Mr','John','Nyugen','john@freshharvest.co.nz','022454535','app/static/assets/img/avatar-08.png',2,1),
(4,4,'Mrs','Jane','Larry','jane@freshharvest.co.nz','0223334535','app/static/assets/img/avatar-05.png',3,1),
(5,5,'Mr','David','Kim','david@freshharvest.co.nz','02573334535','app/static/assets/img/avatar-09.png',1,2),
(6,6,'Mrs','Emily','Stone','emily@freshharvest.co.nz','0223334456','app/static/assets/img/avatar-05.png',2,2),
(7,7,'Miss','Ava','Nobug','ava@freshharvest.co.nz','0254334535','app/static/assets/img/avatar-05.png',3,2),
(8,8,'Miss','Mia','Pairs','mia@freshharvest.co.nz','0276534537','app/static/assets/img/avatar-05.png',1,3),
(9,9,'Mrs','Sophia','London','sophia@freshharvest.co.nz','0265821475','app/static/assets/img/avatar-05.png',2,3),
(10,10,'Mrs','Red','Ng','red@freshharvest.co.nz','022156656','app/static/assets/img/avatar-04.png',3,3),
(11,11,'Mr','Blue','Sean','blue@freshharvest.co.nz','024451256','app/static/assets/img/avatar-07.png',1,4),
(12,12,'Miss','Green','Noah','green@freshharvest.co.nz','022454535','app/static/assets/img/avatar-08.png',2,4),
(13,13,'Mr','Dark','Nowhite','dark@freshharvest.co.nz','02784531','app/static/assets/img/avatar-05.png',3,4),
(14,14,'Mr','Yellow','Kenson','yellow@freshharvest.co.nz','02573334535','app/static/assets/img/avatar-09.png',1,5),
(15,15,'Mr','Cyan','Markson','cyan@freshharvest.co.nz','0223334456','app/static/assets/img/avatar-05.png',2,5),
(16,16,'Miss','Light','Yolo','light@freshharvest.co.nz','0254334535','app/static/assets/img/avatar-05.png',3,5);

CREATE TABLE messages (
    message_id INT AUTO_INCREMENT PRIMARY KEY,
    created_by int not null,
    content text not null,
    time date not null,
	constraint FOREIGN KEY (created_by) REFERENCES users(user_id)
);

INSERT INTO messages (created_by, content, time) VALUES
(1, 'Hello', '2024-01-12'),
(1, 'How can we assist you?', '2024-01-13'),
(1, 'Thank you for your feedback!', '2024-01-14'),
(1, 'We value your support.', '2024-01-15'),
(1, 'Your order is on the way!', '2024-01-16'),
(1, 'Any questions about our products?', '2024-01-17'),
(1, 'We hope you enjoy your purchase.', '2024-01-18'),
(1, 'Stay tuned for more updates.', '2024-01-19'),
(1, 'We are committed to quality.', '2024-01-20'),
(1, 'See you at our next event!', '2024-01-21'),
(1, 'Discount codes are on their way.', '2024-01-22'),
(1, 'New features coming soon!', '2024-01-23'),
(1, 'How can we improve?', '2024-01-24'),
(1, 'Celebrate with us!', '2024-01-25'),
(1, 'Let us know if you need assistance.', '2024-01-26'),
(1, 'Thank you for your loyalty.', '2024-01-27'),
(1, 'New blog post alert!', '2024-01-28'),
(1, 'Product restock!', '2024-01-29'),
(1, 'Upcoming sale!', '2024-01-30'),
(1, 'Thanks for visiting us!', '2024-01-31');



CREATE TABLE news (
    news_id INT AUTO_INCREMENT PRIMARY KEY,
	created_by int not null,
    title VARCHAR(255) NOT NULL,
    content text not null,
    pic varchar(255),
    publish_date date not null,
    depot_id int,
	constraint FOREIGN KEY (created_by) REFERENCES users(user_id)
);

INSERT INTO news (title, publish_date, pic, content, created_by, depot_id) VALUES
('Welcome to Fresh Harvest Delivery', '2024-01-12', 'app/static/assets/img/welcome.jpg', 'Welcome to Fresh Harvest Delivery! Enjoy fresh, seasonal produce with our convenient online service. We offer a variety of fruits, vegetables, herbs, salads, eggs, and honey, delivered to your door. Customise your order or choose from our premade boxes in various sizes and subscriptions. Operating in Christchurch, Invercargill, Wellington, Hamilton, and Auckland, we bring farm-fresh goodness to your table, efficiently managed and delivered by our dedicated local teams.', 1, 0),
('New Product Launch!', '2024-01-15', 'app/static/assets/img/new_product.jpg', 'New Product Launch! Fresh Harvest Delivery is excited to introduce our latest additions: seasonal mixed boxes, fresh herbs, and organic honey. These new products are available for individual purchase or as part of our customisable and subscription boxes. Experience the freshest produce delivered straight to your door, sourced locally and managed seamlessly through our upgraded order management system. Join us in celebrating this launch and enjoy the best of farm-fresh goodness today!', 2, 1),
('Holiday Specials Announced', '2024-01-18', 'app/static/assets/img/holiday_specials.jpg', 'Fresh Harvest Delivery unveils exclusive seasonal delights just in time for the festivities. Treat yourself to a cornucopia of fresh fruits, crisp veggies, aromatic herbs, and more, all curated for the holiday season. Whether you are hosting a feast or simply craving the taste of the holidays, our special offerings are sure to delight. Hurry, these limited-time deals won\'t last long!', 8, 3),
('Extended Business Hours', '2024-01-20', 'app/static/assets/img/business_hours.jpg', 'Extended Business Hours Alert! Fresh Harvest Delivery extends its operational hours for your convenience. Now, you can order your favourite farm-fresh produce even later in the day. Enjoy the flexibility to shop at your leisure and still receive your delivery on time. Take advantage of our extended hours and experience the ease of fresh food shopping like never before!', 2, 1),
('Meet Our New Staff', '2024-01-22', 'app/static/assets/img/new_staff.jpg', 'Meet Our New Staff! Fresh Harvest Delivery proudly introduces the latest additions to our dedicated team. With a passion for fresh produce and customer satisfaction, our new members are ready to ensure your orders are handled with care. Get to know the faces behind your deliveries and experience the personalised service that sets us apart. Welcome aboard our journey to bring farm-fresh goodness to your table!', 11, 4),
('Health and Safety Update', '2024-01-28', 'app/static/assets/img/health_safety.jpg', 'At Fresh Harvest Delivery, your well-being is our top priority. We have implemented rigorous safety measures to ensure the freshness and cleanliness of your produce. From farm to doorstep, every step is taken with your health in mind. Rest assured, you can enjoy our fresh offerings with confidence. Stay healthy, stay safe, and continue to savor the goodness of farm-fresh produce with Fresh Harvest Delivery.', 1, 0),
('Behind the Scenes at Our Facilities', '2024-02-01', 'app/static/assets/img/behind_the_scene.jpg', 'Ever wondered how we ensure the freshness of your produce? Take a peek behind the curtain and discover the inner workings of Fresh Harvest Delivery. From meticulous sorting to efficient packing, witness the dedication of our team in action. Join us on a journey through our facilities and gain insight into the care and precision that goes into every order. Get ready to see firsthand why Fresh Harvest Delivery is your trusted source for farm-fresh goodness!', 5, 2),
('Tips for a Greener Lifestyle', '2024-02-07', 'app/static/assets/img/greener_lifestyle.jpg', 'Fresh Harvest Delivery shares eco-friendly insights to help you live a more sustainable life. From reducing food waste to supporting local farmers, discover simple yet impactful ways to tread lightly on the planet. Join us in our commitment to environmental stewardship and embrace a greener, healthier future. Let\'s make every choice count for a brighter tomorrow!', 8, 3),
('Our Commitment to Quality', '2024-02-10', 'app/static/assets/img/quality_commitment.jpg', 'Fresh Harvest Delivery reaffirms our dedication to providing you with the finest produce. From field to fork, we uphold rigorous standards to ensure freshness, flavor, and nutritional value in every bite. Trust in our unwavering commitment to sourcing the best ingredients and delivering excellence to your doorstep. Experience the difference with Fresh Harvest Delivery – where quality is never compromised.', 2, 1),
('New Opening in Town', '2024-02-12', 'app/static/assets/img/new_opening.jpg', 'Fresh Harvest Delivery is thrilled to announce our newest location in Lincoln! Join us in celebrating the expansion of our farm-fresh offerings to your community. Experience the convenience of locally sourced produce delivered straight to your doorstep. Whether you are a long-time customer or new to our service, we invite you to be part of our growing family. Welcome to the freshness, welcome to Fresh Harvest Delivery in Lincoln', 5, 2),
('Join Our Team!', '2024-02-20', 'app/static/assets/img/join_team.jpg', 'Fresh Harvest Delivery is looking for passionate individuals to join our dedicated team! If you are enthusiastic about fresh produce, customer satisfaction, and making a positive impact, we want to hear from you. Whether you are interested in delivery, customer service, or behind-the-scenes operations, there\'s a place for you at Fresh Harvest Delivery. Join us in bringing farm-fresh goodness to tables across New Zealand and beyond. Let\'s grow together – join our team today!', 11, 4),
('Seasonal Favourites Back in Stock', '2024-02-23', 'app/static/assets/img/seasonal_favourites.jpg', 'Get ready to indulge in the sweet taste of summer as our seasonal favourite, mangosteen, returns! Bursting with flavour and packed with nutrients, mangosteen is a must-have addition to your fruit basket. Don\'t miss out on this limited-time treat – order yours today and savor the exotic goodness of mangosteen, available exclusively at Fresh Harvest Delivery!', 14, 5),
('How We Source Locally', '2024-02-25', 'app/static/assets/img/source_locally.jpg', 'At Fresh Harvest Delivery, supporting local farmers is at the heart of what we do. Discover the journey from farm to table as we unveil our commitment to sourcing the freshest produce from nearby growers. Through partnerships with local farms, we ensure that every item in your order is sustainably sourced and bursting with flavor. Join us in celebrating the flavors of our community and experience the difference of locally sourced goodness with Fresh Harvest Delivery.', 14, 5),
('Exclusive Member Discounts', '2024-02-28', 'app/static/assets/img/member_benefit.jpg', 'Calling all Fresh Harvest Delivery members! Get ready to save big with our exclusive member discounts. Enjoy special offers on your favourite fruits, veggies, and more, available only to our loyal customers. From seasonal specials to member-only deals, there\'s never been a better time to be part of the Fresh Harvest family. Don\'t miss out – join today and start enjoying the perks of membership!', 1, 0);




CREATE TABLE shippments (
    shippment_id INT AUTO_INCREMENT PRIMARY KEY,
	shippment_price int not null,
    depot_id int not null,
	constraint FOREIGN KEY (depot_id) REFERENCES depots(depot_id)
);
INSERT INTO `shippments` (shippment_id,shippment_price, depot_id) VALUES
(1,5,1),
(2,5,2),
(3,5,3),
(4,5,4),
(5,5,5);

CREATE TABLE payment_methods (
    payment_method_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    card_number VARCHAR(255) NOT NULL,
    card_holder_name VARCHAR(255) NOT NULL,
    expiry_date TEXT not null,
    cvc VARCHAR(255) not null,
    constraint FOREIGN KEY (user_id) REFERENCES users(user_id)
);
INSERT INTO payment_methods (payment_method_id,user_id, card_number, card_holder_name, expiry_date, cvc) VALUES 

(1,10,'4111111111111111','Sarah Kim','12/29','290'),
(2,11,'4222222222222222','Jessica Lau','10/30','231'),
(3,13,'4223333333333333','Sarah Power','10/30','123'),
(4,12,'4223333333333333','Sarah Power','10/30','123'),
(5,15,'4223333333333333','Sarah Power','10/30','123'),
(6,14,'4223333333333333','Sarah Power','10/30','123'),
(7,16,'4223333333333333','Sarah Power','10/30','123'),
(8,20,'4223333333333333','Sarah Power','10/30','123'),
(9,17,'4223333333333333','Sarah Power','10/30','123'),
(10,19,'4223333333333333','Sarah Power','10/30','123'),
(12,17,'1234123412341234','sarah','11/25','111'),
(13,17,'4124123412341234','sarah','11/25','111'),
(14,18,'4124111111111111','jessica','11/25','111'),
(15,18,'4124222222222222','jessica','11/25','111'),
(16,19,'4124111122221111','olivia','11/25','111'),
(17,19,'4124222211112222','olivia','11/25','111'),
(18,27,'','','',''),
(19,28,'','','','');

CREATE TABLE payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    payment_method_id INT,
    payment_date DATE NOT NULL,
    status ENUM('Pending', 'Completed', 'Failed', 'Refunded') NOT NULL,
    constraint FOREIGN KEY (user_id) REFERENCES users(user_id),
    constraint FOREIGN KEY (payment_method_id) REFERENCES payment_methods(payment_method_id)
);

INSERT INTO `payments` (payment_id,user_id, amount,payment_method_id,payment_date,`status`) VALUES
(1,17,79.7,12,'2024-06-01','Completed'),
(2,17,108.5,13,'2024-06-09','Completed'),
(3,18,80.96,14,'2024-06-01','Completed'),
(4,18,88.89,15,'2024-06-09','Completed'),
(5,19,72.82,16,'2024-06-01','Completed'),
(6,19,62.93,17,'2024-06-09','Completed'),
(7,27,78.13,18,'2024-04-01','Completed'),
(8,27,133.84,18,'2024-06-10','Completed'),
(9,28,135.77,19,'2024-04-01','Completed'),
(10,28,127.44,19,'2024-06-10','Completed');

CREATE TABLE orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    order_date date NOT NULL,
    payment_id INT,
    shippment_id int NOT NULL,
    constraint FOREIGN KEY (user_id) REFERENCES users(user_id),
    constraint FOREIGN KEY (payment_id) REFERENCES payments(payment_id),
	constraint FOREIGN KEY (shippment_id) REFERENCES shippments(shippment_id)
);

INSERT INTO `orders` (order_id,user_id,order_date, payment_id,shippment_id) VALUES
 (1,17,'2024-06-01',1,1),
 (2,17,'2024-06-09',2,1),
 (3,18,'2024-06-01',3,1),
 (4,18,'2024-06-09',4,1),
 (5,19,'2024-06-01',5,2),
 (6,19,'2024-06-09',6,2),
 (7,27,'2024-06-01',7,1),
 (8,27,'2024-06-10',8,1),
 (9,28,'2024-06-01',9,1),
 (10,28,'2024-06-10',10,1);

CREATE TABLE receipts (
    receipt_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    gst DECIMAL(10, 2) NOT NULL,
    constraint FOREIGN KEY (order_id) REFERENCES orders(order_id)
);
INSERT INTO `receipts` (receipt_id,order_id,gst) VALUES
(1,1,0.15),
(2,2,0.15),
(3,3,0.15),
(4,4,0.15),
(5,5,0.15),
(6,6,0.15),
(7,7,0.15),
(8,8,0.15),
(9,9,0.15),
(10,10,0.15);


CREATE TABLE order_status_types (
    order_status_type_id INT AUTO_INCREMENT PRIMARY KEY,
    order_status_type_name ENUM('Preparing', 'Ready for delivery', 'On delivery vehicle', 'Delivered') NOT NULL
);
insert into order_status_types (order_status_type_id, order_status_type_name) values
(1,'Preparing'),
(2,'Ready for delivery'),
(3,'On delivery vehicle'),
(4,'Delivered');


CREATE TABLE order_assignments (
    order_id INT,
    order_status_type_id INT,
    staff_id int not null,
	start_date date not null,
    primary key (order_id, order_status_type_id),
	constraint FOREIGN KEY (order_id) REFERENCES orders(order_id),
    constraint FOREIGN KEY (order_status_type_id) REFERENCES order_status_types(order_status_type_id)
);
insert into order_assignments (order_id,order_status_type_id,staff_id,start_date) values
(1,1,3,'2024-06-01'),
(1,2,3,'2024-06-01'),
(1,3,4,'2024-06-01');

CREATE TABLE product_categories (
    product_category_id INT AUTO_INCREMENT PRIMARY KEY,
	product_category_name VARCHAR(255) not null
);

insert into product_categories (product_category_id,product_category_name) values
(1,'Fruit'),
(2,'Vegetables'),
(3,'Fresh Herbs'),
(4,'Salads'),
(5,'Eggs'),
(6,'Honey'),
(7,'Box'),
(8,'Giftcard');



CREATE TABLE promotion_types (
    promotion_type_id INT AUTO_INCREMENT PRIMARY KEY,
    promotion_type_name varchar(255) NOT NULL,
    discount DECIMAL(10,2) NOT NULL
);

insert into promotion_types (promotion_type_id,promotion_type_name,discount) values
(1, '',1.00),
(2, 'In Season',0.90),
(3, '20% OFF',0.80),
(4, '30% OFF',0.70),
(5, '40% OFF',0.60),
(6, '50% OFF',0.50),
(7, 'Weekly Specials',0.50);



CREATE TABLE product (
    product_name VARCHAR(255) not null,   
    SKU VARCHAR(255) NOT NULL,
    unit int not null, 
    pic VARCHAR(255),
    product_des TEXT,
    product_origins TEXT,
	primary key (SKU),
	constraint FOREIGN KEY (unit) REFERENCES units(unit_id)

);
insert into product (product_name,SKU,unit,pic,product_des,product_origins) values
('Apples Granny Smith','YFK68885',1,'app/static/assets/img/Apples-Granny-Smith.jpg','Approx 4-5 medium apples per 1kg - but actual quantity may vary. Available: late march/april - november a crisp, juicy dessert apple with a tangy, zesty flavour. excellent for cooking and sauces.','Product of New Zealand'),
('Apples Royal Gala','ZUC77886',1,'app/static/assets/img/Apples-Royal-Gala.jpg','Approx 4-5 medium apples per 1kg - but actual quantity may vary. A very popular eating apple. A sweet flavoured apple with a crisp juicy flesh. Best eaten fresh. Smaller sizes are ideal for kids lunch boxes.','Product of New Zealand'),
('Pears Packham Green','GXO04612',1,'app/static/assets/img/Pears-Packham-Green.jpg','Packham pears have juicy white flesh. They are rich in flavour, too, so are great eaten solo, baked in tarts, or poached and infused.','Product of New Zealand'),
('Pears Nashi','PTX58876',1,'app/static/assets/img/Pear-Nashi.jpg','Nashi pears are gold in colour, are sweet, aromatic and juicy but firm flesh.','Product of New Zealand'),
('Mint','RNU22535',4,'app/static/assets/img/Mint.jpg','Mint complements a range of dishes like tabbouleh, steamed green peas and carrots but also smoothies and summer drinks.','Product of New Zealand'),
('Lettuce','ODN17732',4,'app/static/assets/img/Lettuce.jpg','Coral green lettuce have attractive crinkly leaves and a sharp, slightly bitter flavour. The depth of green colour depends on the variety and the season. The leaves should be picked separately as these lettuces are often sold with intact roots. use coral green lettuce in sandwiches and wraps or with a variety of other lettuce in a salad to increase interest.','Product of New Zealand'),
('Coleslaw Salad','BRQ73679',1,'app/static/assets/img/Coleslaw.jpg','Leaderbrand coleslaw is a flavour-filled combination of shredded green cabbage and carrot. washed and ready to eat. includes an individually packaged homestyle dressing, which contains no artificial colours, flavours or preservatives.','Product of New Zealand'),
('Eggs size 7 18 PACK','WAA56533',6,'app/static/assets/img/egg.jpg','Cage Free Barn Eggs','Product of New Zealand'),
('Multifloral Honey 500g','IYT14517',4,'app/static/assets/img/Multifloral-Honey.jpg','100% genuine export quality new zealand multifloral manuka honey. Independently tested to show it meets the new zealand government\'s definition of multifloral manuka honey. The number on the front of the pot represents the mg per kg of mgo (methylglyoxal). Mgo is naturally made in the hive from dha, which is present in the nectar of the manuka bush.','Product of New Zealand'),
('Mandarins','JUS30319',1,'app/static/assets/img/Mandarins.jpg','Fresh, juicy mandarins. Easy to peel and great for snacking.','Product of New Zealand'),
('Blueberries','MLR73585',5,'app/static/assets/img/Blueberries.jpg','Fresh blueberries, rich in antioxidants and perfect for snacking or baking.','Product of New Zealand'),
('Spinach','GUM61827',13,'app/static/assets/img/Spinach.jpg','Fresh spinach leaves, rich in iron and vitamins. Great for salads and cooking.','Product of New Zealand'),
('Carrots','BCD92061',1,'app/static/assets/img/Carrots.jpg','Fresh, crunchy carrots. Ideal for cooking or snacking.','Product of New Zealand'),
('Broccoli','CCA03384',4,'app/static/assets/img/Broccoli.jpg','Fresh, crisp broccoli. Perfect for steaming, roasting, or adding to stir-fries.','Product of New Zealand'),
('Capsicums','JNO78084',1,'app/static/assets/img/Capsicums.jpg','Sweet and crunchy capsicums. Great for salads and stir-fries.','Product of New Zealand'),
('Avocados','KDW03463',4,'app/static/assets/img/Avocados.jpg','Creamy avocados, perfect for salads, sandwiches, and guacamole.','Product of New Zealand'),
('Strawberries','EFA75558',5,'app/static/assets/img/Strawberries.jpg','Sweet, juicy strawberries. Great for snacking and desserts.','Product of New Zealand'),
('Pineapple','PFV76691',4,'app/static/assets/img/Pineapple.jpg','Sweet and juicy pineapples, perfect for snacking or adding to fruit salads.','Product of New Zealand'),
('Kiwifruit','XMV78720',1,'app/static/assets/img/Kiwifruit.jpg','Fresh, tangy kiwifruit. Great for snacking and adding to desserts.','Product of New Zealand'),
('Red Onions','GUT35265',1,'app/static/assets/img/Red-Onions.jpg','Sweet and crunchy red onions. Perfect for salads, sandwiches, and cooking.','Product of New Zealand'),
('Cauliflower','DVE74986',4,'app/static/assets/img/Cauliflower.jpg','Fresh cauliflower, ideal for roasting, steaming, or adding to curries and stir-fries.','Product of New Zealand'),
('Basil','VGO53827',11,'app/static/assets/img/Basil.jpg','Perfect for adding a fresh taste to any meal, especially good in Italian cuisine.','Product of New Zealand'),
('Cilantro','XOW80009',11,'app/static/assets/img/Cilantro.jpg','A fragrant, antioxidant-rich herb essential for Mexican dishes.','Product of New Zealand'),
('Parsley','RLW15631',11,'app/static/assets/img/Parsley.jpg','Bright flavor, perfect for garnishing and adding extra zest to dishes.','Product of New Zealand'),
('Rosemary','MOM12971',11,'app/static/assets/img/Rosemary.jpg','Woody aroma, perfect for grilling and roasting.','Product of New Zealand'),
('Premium Mint','YQY98243',11,'app/static/assets/img/pMint.jpg','Refreshing and cool, ideal for drinks and desserts.','Product of New Zealand'),
('Sage','QCL08399',11,'app/static/assets/img/Sage.jpg','Earthy flavor, commonly used in stuffings and pairs well with poultry.','Product of New Zealand'),
('Chives','TMP54497',11,'app/static/assets/img/Chives.jpg','Mild onion flavor, excellent in salads and as garnishes.','Product of New Zealand'),
('Oregano','RFY12369',11,'app/static/assets/img/Oregano.jpg','Robust taste, essential for Italian, Greek, and Spanish cooking.','Product of New Zealand'),
('Dill','GXQ02373',11,'app/static/assets/img/Dill.jpg','Delicate and aromatic, ideal for seasoning fish and salad dressings.','Product of New Zealand'),
('Thyme','KYG05712',11,'app/static/assets/img/Thyme.jpg','Highly aromatic, great for enhancing the flavors of meat dishes.','Product of New Zealand'),
('Garden Salad','HYW32723',1,'app/static/assets/img/GardenSalad.jpg','Freshly picked greens with a variety of garden vegetables.','Product of New Zealand'),
('Kale Salad','WQZ54262',1,'app/static/assets/img/KaleSalad.jpg','Nutrient-packed kale with a lemon dressing, perfect for a health boost.','Product of New Zealand'),
('Spinach Salad','CIY46758',1,'app/static/assets/img/SpinachSalad.jpg','Tender spinach leaves with nuts and a sweet dressing.','Product of New Zealand'),
('Arugula Salad','VMP50894',1,'app/static/assets/img/ArugulaSalad.jpg','Peppery arugula with pine nuts and Parmesan, drizzled with balsamic glaze.','Product of New Zealand'),
('Cobb Salad','XPY76160',1,'app/static/assets/img/CobbSalad.jpg','Loaded with chicken, eggs, blue cheese, and crispy bacon.','Product of New Zealand'),
('Waldorf Salad','GSB55804',1,'app/static/assets/img/WaldorfSalad.jpg','A mix of apple, celery, and walnuts, coated in a light mayonnaise dressing.','Product of New Zealand'),
('Bean Salad','GBH48577',1,'app/static/assets/img/BeanSalad.jpg','A hearty blend of beans with a tangy vinaigrette.','Product of New Zealand'),
('Quinoa Salad','WWQ05108',1,'app/static/assets/img/QuinoaSalad.jpg','Quinoa with roasted vegetables and a hint of lime.','Product of New Zealand'),
('Caesar Salad','RFM66584',1,'app/static/assets/img/CaesarSalad.jpg','Classic Caesar salad with crisp romaine lettuce, Parmesan cheese, and croutons.','Product of New Zealand'),
('Greek Salad','TBC47322',1,'app/static/assets/img/GreekSalad.jpg','A healthy mix of cucumber, tomatoes, feta cheese, and olives.','Product of New Zealand'),
('Free Range Eggs','IPS35432',10,'app/static/assets/img/FreeRangeEggs.jpg','12 high-quality free-range eggs.','Product of New Zealand'),
('Organic Eggs','AIG90771',10,'app/static/assets/img/OrganicEggs.jpg','Organically farmed and nutritious.','Product of New Zealand'),
('Barn Laid Eggs','PLS16272',10,'app/static/assets/img/BarnLaidEggs.jpg','Affordable yet high-quality barn-laid eggs.','Product of New Zealand'),
('Omega-3 Enriched Eggs','DLF19091',10,'app/static/assets/img/Omega3Eggs.jpg','Eggs enriched with Omega-3 for additional health benefits.','Product of New Zealand'),
('Pasture Raised Eggs','ZNW55725',10,'app/static/assets/img/PastureRaisedEggs.jpg','Eggs from chickens raised in pastures, ensuring high quality.','Product of New Zealand'),
('Cage-Free Large Eggs','BRF37284',10,'app/static/assets/img/CageFreeEggs.jpg','Cage-free eggs laid from chickens living in improved conditions.','Product of New Zealand'),
('Jumbo Eggs','KEH65247',10,'app/static/assets/img/JumboEggs.jpg','Extra-large eggs perfect for baking.','Product of New Zealand'),
('Medium White Eggs','ACH75642',10,'app/static/assets/img/WhiteEggs.jpg','Standard medium-sized white eggs.','Product of New Zealand'),
('Large Brown Eggs','LBS92592',10,'app/static/assets/img/BrownEggs.jpg','Large, rich-flavored brown eggs.','Product of New Zealand'),
('Small Eggs','VLO39296',10,'app/static/assets/img/SmallEggs.jpg','Smaller eggs, often preferred for diet control.','Product of New Zealand'),
('Manuka Honey UMF 10+','GQH96483',3,'app/static/assets/img/ManukaHoney.jpg','Premium Manuka honey with a UMF 10+ rating.','Product of New Zealand'),
('Clover Honey','UTN05805',12,'app/static/assets/img/CloverHoney.jpg','Sweet and light, perfect for teas and cooking.','Product of New Zealand'),
('Wildflower Honey','PAT55307',12,'app/static/assets/img/WildflowerHoney.jpg','A mix of nectar from various wildflowers, rich in flavor.','Product of New Zealand'),
('Beechwood Honeydew','VDN50187',12,'app/static/assets/img/BeechwoodHoney.jpg','Dark and rich honeydew honey collected from beechwood forests.','Product of New Zealand'),
('Thyme Honey','WOQ25398',3,'app/static/assets/img/ThymeHoney.jpg','Distinctive thyme-flavored honey, aromatic and healing properties.','Product of New Zealand'),
('Rata Honey','TUL06067',3,'app/static/assets/img/RataHoney.jpg','Rare honey made from the nectar of the native Rata tree.','Product of New Zealand'),
('Kamahi Honey','GTJ94978',12,'app/static/assets/img/KamahiHoney.jpg','Rich and golden, a perfect sweetener with a complex flavor.','Product of New Zealand'),
('Tawari Honey','IIL80704',12,'app/static/assets/img/TawariHoney.jpg','Light and creamy with a butterscotch flavor.','Product of New Zealand'),
('Pohutukawa Honey','FUU83971',3,'app/static/assets/img/PohutukawaHoney.jpg','Distinctive and rare, sourced from the coastal Pohutukawa tree.','Product of New Zealand'),
('Linden Honey','JDO58555',12,'app/static/assets/img/LindenHoney.jpg','Delicately sweet with a hint of mint, excellent for relaxation.','Product of New Zealand'),
('Grapes Green','APA11223',12,'app/static/assets/img/GrapesGreen.jpg','Crisp and juicy green grapes, known for their sweet and slightly tart flavour.','Product of New Zealand'),
('Apple Jazz','AJA11223',1,'app/static/assets/img/AppleJazz.jpg','Crisp and refreshing, JAZZ apples offer a perfect balance of sweet and tangy flavours.','Product of New Zealand'),
('Feijoa','FPA11221',1,'app/static/assets/img/Feijoa.jpg','Tropical feijoa, with its unique sweet and tangy flavor, perfect for fresh eating, smoothies, or desserts.','Product of New Zealand'),
('Potatoes','PAP11232',1,'app/static/assets/img/Potatoes.jpg','Versatile potatoes, ideal for baking, boiling, mashing, or frying, offering a hearty and nutritious addition to any meal.','Product of New Zealand'),
('Lemon','LPP23323',1,'app/static/assets/img/Lemon.jpg','Zesty lemons, known for their bright, tangy flavour and vibrant aroma, perfect for enhancing drinks, marinades, dressings, and desserts.','Product of New Zealand'),
('Kumara Orange','KOK23332',1,'app/static/assets/img/KumaraOrange.jpg','Sweet and nutritious orange kumara, with its rich, creamy texture and natural sweetness, perfect for roasting, mashing, or adding to soups and stews.','Product of New Zealand'),
('Mushrooms White Button','MWB23343',3,'app/static/assets/img/MushroomsWhiteButton.jpg','Versatile white button mushrooms, ideal for enhancing any dish with their mild and earthy flavour.','Product of New Zealand'),
('Coriander','CPA22334',11,'app/static/assets/img/Coriander.jpg','Fragrant coriander, adding a burst of fresh flavour to salads, curries, soups, and stir-fries with its citrusy and aromatic notes.','Product of New Zealand'),
('Courgette','CPP32123',1,'app/static/assets/img/Courgette.jpg','Tender courgettes, perfect for grilling or roasting, offering a mild and versatile addition to salads, pastas, and stir-fries.','Product of New Zealand'),
('Mushrooms Portobello','MMP32221',3,'app/static/assets/img/MushroomsPortobello.jpg','Hearty portobello mushrooms, ideal for grilling, stuffing, or using as a meaty alternative in burgers or sandwiches, offering a robust flavour and meaty texture.','Product of New Zealand'),
('Cucumber','CPP33123',2,'app/static/assets/img/Cucumber.jpg','Crisp and refreshing cucumbers, perfect for salads, sandwiches, or simply enjoyed as a hydrating snack.','Product of New Zealand'),
('Snow Peas','SPS33223',6,'app/static/assets/img/SnowPeas.jpg','Snow peas, tender and sweet, perfect for stir-fries, salads, or enjoying raw as a crunchy and nutritious snack.','Product of New Zealand'),
('Parsnip','PAR44433',1,'app/static/assets/img/Parsnip.jpg','Sweet and earthy parsnips, ideal for roasting, mashing, or adding to soups and stews, offering a delightful flavour reminiscent of carrots with a hint of spice.','Product of New Zealand'),
('Mushrooms Swiss Brown','MSB44332',3,'app/static/assets/img/MushroomsSwissBrown.jpg','Rich and flavourful Swiss brown mushrooms, perfect for grilling or adding depth to soups, stews, and sauces with their robust and earthy taste.','Product of New Zealand'),
('Cabbage','CAB44123',2,'app/static/assets/img/Cabbage.jpg','Crunchy cabbage, versatile for coleslaws, stir-fries, or fermenting into tangy sauerkraut, adding a crisp texture and mild flavour to your dishes.','Product of New Zealand'),
('Pumpkin Butternut','PBT44123',2,'app/static/assets/img/PumpkinButternut.jpg','Sweet and creamy butternut pumpkin, perfect for roasting, soups, or adding a comforting touch to any dish with its rich flavour and smooth texture.','Product of New Zealand'),
('Brussel Sprouts','BST55123',13,'app/static/assets/img/BrusselSprouts.jpg','Tender brussels sprouts, ideal for roasting or adding to salads, offering a delightful nutty flavour and satisfying crunch.','Product of New Zealand'),
('Eggplant','EGG55112',2,'app/static/assets/img/Eggplant.jpg','Versatile eggplant, perfect for grilling, roasting, or sautéing, adding a meaty texture and subtle flavour to curries, stir-fries, or Mediterranean dishes.','Product of New Zealand'),
('Squash Buttercup','SBP55432',2,'app/static/assets/img/SquashButtercup.jpg','Sweet and creamy buttercup squash, perfect for roasting, soups, or mashing into comforting dishes with its rich flavour and smooth texture.','Product of New Zealand'),
('Pumpkin Crown','PUC55231',2,'app/static/assets/img/PumpkinCrown.jpg','Regal Crown pumpkins, renowned for their sweet flavor and smooth texture, perfect for roasting, soups, or baking into pies and muffins, adding a touch of autumnal delight to any dish.','Product of New Zealand');

	CREATE TABLE subscriptions (
    subscription_id INT AUTO_INCREMENT PRIMARY KEY,
    subscription_name ENUM('One-off', 'Weekly', 'Biweekly', 'Monthly') NOT NULL
);
insert into subscriptions (subscription_id,subscription_name) values
(1,'One-off'),
(2,'Weekly'),
(3,'Biweekly'),
(4,'Monthly');

CREATE TABLE boxes (
	SKU VARCHAR(255) NOT NULL,
    box_name VARCHAR(255) not null,   
    unit int not null, 
    pic VARCHAR(255),
    box_des TEXT,
    product_origins TEXT,

    primary key (SKU),
	
    constraint FOREIGN KEY (unit) REFERENCES units(unit_id)

);


insert into boxes (SKU,box_name,unit,pic,box_des,product_origins) values
('BOX00001','Autumn Harvest',7,'app/static/assets/img/boxa.jpg','Celebrate the bounty of the season with the Autumn Harvest box, filled with fresh, locally-sourced produce. Perfect for hearty meals and seasonal recipes.','Product of New Zealand'),
('BOX00002','Summer Delight',8,'app/static/assets/img/boxb.jpg','Experience the vibrant flavors of summer with the Summer Delight box. Packed with juicy fruits and crisp vegetables to brighten up your meals.','Product of New Zealand'),
('BOX00003','Farmer\'s Choice',8,'app/static/assets/img/boxc.jpg','Enjoy a handpicked selection of farm-fresh produce with the Farmer\'s Choice box. Ideal for those who appreciate quality and variety in their diet.','Product of New Zealand'),
('BOX00004','Organic Veggie Mix',9,'app/static/assets/img/boxa.jpg','Savor the best of organic farming with the Organic Veggie Mix box. A perfect choice for health-conscious consumers looking for pesticide-free vegetables.','Product of New Zealand'),
('BOX00005','Seasonal Fresh Box',9,'app/static/assets/img/boxb.jpg','Relish the freshest produce of the season with the Seasonal Fresh Box. Each box contains a diverse range of fruits and vegetables to suit all tastes.','Product of New Zealand'),
('BOX00006','Harvest Special',7,'app/static/assets/img/boxc.jpg','Discover the richness of New Zealand’s agriculture with the Harvest Special box. A curated selection of the finest produce to enhance your culinary creations.','Product of New Zealand'),
('BOX00007','Healthy Essentials',7,'app/static/assets/img/boxa.jpg','Keep your diet on track with the Healthy Essentials box. Packed with nutrient-rich fruits and vegetables, this box is perfect for a balanced diet.','Product of New Zealand'),
('BOX00008','Exotic Fruit Box',9,'app/static/assets/img/basket-juicy.jpg','Indulge in a variety of exotic fruits with the Exotic Fruit Box. A delightful selection for those who love to explore unique and flavorful fruits.','Product of New Zealand'),
('BOX00009','Juicy Fruit Pack',8,'app/static/assets/img/basket-juicy.jpg','Enjoy the freshest and juiciest fruits with the Juicy Fruit Pack. Ideal for snacks, desserts, or adding a sweet touch to your meals.','Product of New Zealand'),
('BOX00010','Classic Fruit Basket',8,'app/static/assets/img/basket-fruit.jpg','The Classic Fruit Basket offers a timeless selection of delicious fruits. Perfect for gifting or enjoying a wholesome treat at home.','Product of New Zealand');

CREATE TABLE giftcards (
	SKU VARCHAR(255) NOT NULL,
    giftcard_name VARCHAR(255) not null,   
    pic VARCHAR(255),
    giftcard_des TEXT,
    primary key (SKU)

);
INSERT INTO giftcards (SKU, giftcard_name, pic,giftcard_des) VALUES
('GIFT0010','$10NZD giftcard','app/static/assets/img/giftcard.jpg','Our gift cards have no additional processing fees. You can use them on our website at any time for any purchase!'),
('GIFT0020','$20NZD giftcard','app/static/assets/img/giftcard.jpg','Our gift cards have no additional processing fees. You can use them on our website at any time for any purchase!'),
('GIFT0030','$30NZD giftcard','app/static/assets/img/giftcard.jpg','Our gift cards have no additional processing fees. You can use them on our website at any time for any purchase!'),
('GIFT0040','$40NZD giftcard','app/static/assets/img/giftcard.jpg','Our gift cards have no additional processing fees. You can use them on our website at any time for any purchase!'),
('GIFT0050','$50NZD giftcard','app/static/assets/img/giftcard.jpg','Our gift cards have no additional processing fees. You can use them on our website at any time for any purchase!'),
('GIFT0060','$60NZD giftcard','app/static/assets/img/giftcard.jpg','Our gift cards have no additional processing fees. You can use them on our website at any time for any purchase!'),
('GIFT0070','$70NZD giftcard','app/static/assets/img/giftcard.jpg','Our gift cards have no additional processing fees. You can use them on our website at any time for any purchase!'),
('GIFT0080','$80NZD giftcard','app/static/assets/img/giftcard.jpg','Our gift cards have no additional processing fees. You can use them on our website at any time for any purchase!'),
('GIFT0090','$90NZD giftcard','app/static/assets/img/giftcard.jpg','Our gift cards have no additional processing fees. You can use them on our website at any time for any purchase!'),
('GIFT0100','$100NZD giftcard','app/static/assets/img/giftcard.jpg','Our gift cards have no additional processing fees. You can use them on our website at any time for any purchase!');

CREATE TABLE union_skus (
    SKU VARCHAR(50) PRIMARY KEY,
    source ENUM('product', 'boxes', 'giftcards')
);

INSERT INTO union_skus (SKU, source)
SELECT SKU, 'product' FROM product
UNION ALL
SELECT SKU, 'boxes' FROM boxes
UNION ALL
SELECT SKU, 'giftcards' FROM giftcards;



CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    SKU VARCHAR(255) DEFAULT NULL,
    product_price DECIMAL(10,2) NOT NULL,
    product_category_id int not null,
    promotion_type_id int,    
    depot_id int not null,
    product_status BOOLEAN DEFAULT TRUE,
	constraint FOREIGN KEY (promotion_type_id) REFERENCES promotion_types(promotion_type_id),
    constraint FOREIGN KEY (product_category_id) REFERENCES product_categories(product_category_id),
	constraint FOREIGN KEY (depot_id) REFERENCES depots(depot_id),
	constraint FOREIGN KEY (SKU) REFERENCES union_skus(sku)
);
insert into products (product_id,SKU,product_price,product_category_id,promotion_type_id,depot_id,product_status) values
(1,'YFK68885',2.99,1,1,1,1),
(2,'ZUC77886',1.99,1,1,1,1),
(3,'GXO04612',2.99,1,1,1,1),
(4,'PTX58876',4.99,1,1,1,1),
(5,'RNU22535',4.29,3,1,1,1),
(6,'ODN17732',3.99,2,1,1,1),
(7,'BRQ73679',9.99,4,1,1,1),
(8,'WAA56533',13,5,1,1,1),
(9,'IYT14517',20,6,1,1,1),
(10,'YFK68885',2.99,1,1,2,1),
(11,'ZUC77886',1.99,1,1,2,1),
(12,'GXO04612',2.99,1,1,2,1),
(13,'PTX58876',4.99,1,1,2,1),
(14,'RNU22535',4.29,3,1,2,1),
(15,'ODN17732',3.99,2,1,2,1),
(16,'BRQ73679',9.99,4,1,2,1),
(17,'WAA56533',13,5,1,2,1),
(18,'IYT14517',20,6,1,2,1),
(19,'JUS30319',2.79,1,1,1,1),
(20,'MLR73585',5.99,1,1,2,1),
(21,'GUM61827',3.99,2,1,3,1),
(22,'BCD92061',1.49,2,1,4,1),
(23,'CCA03384',2.99,2,1,5,1),
(24,'JNO78084',5.49,2,1,2,1),
(25,'KDW03463',2.49,1,1,4,1),
(26,'EFA75558',6.99,1,1,5,1),
(27,'PFV76691',3.99,1,1,3,1),
(28,'XMV78720',3.49,1,1,1,1),
(29,'GUT35265',2.99,2,1,2,1),
(30,'DVE74986',4.99,2,1,4,1),
(31,'VGO53827',3.75,3,1,1,1),
(32,'XOW80009',2.5,3,1,2,1),
(33,'RLW15631',2.9,3,1,3,1),
(34,'MOM12971',3.5,3,1,1,1),
(35,'YQY98243',2.99,3,1,2,1),
(36,'QCL08399',3.45,3,1,3,1),
(37,'TMP54497',2.75,3,1,4,1),
(38,'RFY12369',3.2,3,1,5,1),
(39,'GXQ02373',3.3,3,1,4,1),
(40,'KYG05712',3,3,1,5,1),
(41,'HYW32723',3.99,4,1,3,1),
(42,'WQZ54262',5.25,4,1,4,1),
(43,'CIY46758',4.75,4,1,5,1),
(44,'VMP50894',4.5,4,1,1,1),
(45,'XPY76160',6.99,4,1,2,1),
(46,'GSB55804',5.75,4,1,3,1),
(47,'GBH48577',4.25,4,1,4,1),
(48,'WWQ05108',6.5,4,1,5,1),
(49,'RFM66584',4.99,4,1,1,1),
(50,'TBC47322',5.5,4,1,2,1),
(51,'IPS35432',6.5,5,1,1,1),
(52,'AIG90771',8.5,5,1,2,1),
(53,'PLS16272',5,5,1,3,1),
(54,'DLF19091',9,5,1,4,1),
(55,'ZNW55725',7.5,5,1,5,1),
(56,'BRF37284',6.9,5,1,1,1),
(57,'KEH65247',7.5,5,1,2,1),
(58,'ACH75642',4.5,5,1,3,1),
(59,'LBS92592',6.75,5,1,4,1),
(60,'VLO39296',4,5,1,5,1),
(61,'GQH96483',25,6,1,1,1),
(62,'UTN05805',15,6,1,2,1),
(63,'PAT55307',20,6,1,3,1),
(64,'VDN50187',22,6,1,4,1),
(65,'WOQ25398',24,6,1,5,1),
(66,'TUL06067',23,6,1,1,1),
(67,'GTJ94978',18,6,1,2,1),
(68,'IIL80704',21,6,1,3,1),
(69,'FUU83971',27,6,1,4,1),
(70,'JDO58555',19,6,1,5,1),
(71,'BOX00001',20,7,1,1,1),
(72,'BOX00002',45,7,2,1,1),
(73,'BOX00003',20,7,3,1,1),
(74,'BOX00004',45,7,4,1,1),
(75,'BOX00005',20,7,5,1,1),
(76,'BOX00006',45,7,6,1,1),
(77,'BOX00007',20,7,5,1,1),
(78,'BOX00008',45,7,4,1,1),
(79,'BOX00009',20,7,3,1,1),
(80,'BOX00010',45,7,1,1,1),
(81,'BOX00001',20,7,1,2,1),
(82,'BOX00002',45,7,2,2,1),
(83,'BOX00003',20,7,3,2,1),
(84,'BOX00004',45,7,4,2,1),
(85,'BOX00005',20,7,5,2,1),
(86,'BOX00006',45,7,6,2,1),
(87,'BOX00007',20,7,5,2,1),
(88,'BOX00008',45,7,4,2,1),
(89,'BOX00009',20,7,3,2,1),
(90,'BOX00010',45,7,1,2,1),
(91,'BOX00001',20,7,1,3,1),
(92,'BOX00002',45,7,2,3,1),
(93,'BOX00003',20,7,3,3,1),
(94,'BOX00004',45,7,4,4,1),
(95,'BOX00005',20,7,5,4,1),
(96,'BOX00006',45,7,6,4,1),
(97,'BOX00007',20,7,5,4,1),
(98,'BOX00008',45,7,4,4,1),
(99,'BOX00009',20,7,3,5,1),
(100,'BOX00010',45,7,1,5,1),
(101,'APA11223',7.99,1,7,1,1),
(102,'AJA11223',2.99,1,7,1,1),
(103,'FPA11221',6.99,1,3,1,1),
(104,'PAP11232',2.69,2,7,1,1),
(105,'LPP23323',5.99,1,7,2,1),
(106,'KOK23332',7.99,2,7,2,1),
(107,'MWB23343',4.99,2,7,2,1),
(108,'CPA22334',2.99,3,4,2,1),
(109,'CPP32123',7.99,2,7,3,1),
(110,'MMP32221',5.99,2,7,3,1),
(111,'CPP33123',2.99,2,7,3,1),
(112,'SPS33223',4.99,2,3,3,1),
(113,'PAR44433',3.59,2,7,4,1),
(114,'MSB44332',4.99,2,7,4,1),
(115,'CAB44123',3.99,2,2,4,1),
(116,'PBT44123',4.50,2,7,4,1),
(117,'BST55123',6.99,2,7,5,1),
(118,'EGG55112',3.99,2,7,5,1),
(119,'SBP55432',6.99,2,7,5,1),
(120,'PUC55231',6.50,2,2,5,1);



CREATE TABLE box_items (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    SKU VARCHAR(255) DEFAULT NULL,
    product_id int NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    constraint FOREIGN KEY (product_id) REFERENCES products(product_id),
    constraint FOREIGN KEY (SKU) REFERENCES union_skus(sku)
);

insert into box_items(item_id,SKU,product_id,quantity) values
(1,'BOX00001',1,2),
(2,'BOX00001',2,2),
(3,'BOX00002',3,2),
(4,'BOX00002',4,2),
(5,'BOX00003',5,2),
(6,'BOX00003',6,2),
(7,'BOX00004',7,2),
(8,'BOX00004',8,2),
(9,'BOX00005',9,2),
(10,'BOX00005',10,2),
(11,'BOX00006',11,2),
(12,'BOX00006',12,2),
(13,'BOX00007',13,2),
(14,'BOX00007',14,2),
(15,'BOX00008',15,2),
(16,'BOX00008',16,2),
(17,'BOX00009',17,2),
(18,'BOX00009',18,2),
(19,'BOX00010',19,2);

CREATE TABLE order_lines (
    line_number INT AUTO_INCREMENT PRIMARY KEY,
	order_id INT not null,
    product_id int not null,
    product_quantity int not null,
	constraint FOREIGN KEY (order_id) REFERENCES orders(order_id),
	constraint foreign key (product_id) references products(product_id)
);

INSERT INTO `order_lines` (line_number,order_id,product_id,product_quantity) VALUES
(1,1,56,3),
(2,1,9,2),
(3,1,34,4),
(4,2,72,1),
(5,2,78,2),
(6,3,51,2),
(7,3,49,2),
(8,3,66,2),
(9,3,28,2),
(10,4,7,1),
(11,4,3,5),
(12,4,6,5),
(13,4,8,3),
(14,5,18,2),
(15,5,14,3),
(16,5,10,5),
(17,6,24,4),
(18,6,57,2),
(19,6,45,3),
(20,7,7,3),
(21,7,5,4),
(22,7,8,2),
(23,8,4,6),
(24,8,66,3),
(25,8,1,10),
(26,9,6,10),
(27,9,5,3),
(28,9,8,6),
(29,10,7,5),
(30,10,66,3),
(31,10,28,1);


CREATE TABLE stock (
    product_id INT,
	depot_id INT,
	quantity DECIMAL(10,2) NOT NULL,
    primary key (product_id,depot_id),
	constraint FOREIGN KEY (product_id) REFERENCES products(product_id),
    constraint FOREIGN KEY (depot_id) REFERENCES depots(depot_id)
);

insert into stock (product_id, depot_id,quantity) values
(1,1,100),
(2,1,100),
(3,1,200),
(4,1,110),
(5,1,156),
(6,1,167),
(7,1,701),
(8,1,188),
(9,1,161),
(10,2,192),
(11,2,53),
(12,2,158),
(13,2,87),
(14,2,400),
(15,2,220),
(16,2,126),
(17,2,0),
(18,2,606),
(19,1,760),
(20,2,79),
(21,3,42),
(22,4,182),
(23,5,63),
(24,2,178),
(25,4,144),
(26,5,71),
(27,3,16),
(28,1,2),
(29,2,95),
(30,4,147),
(31,1,113),
(32,2,47),
(33,3,176),
(34,1,196),
(35,2,40),
(36,3,75),
(37,4,160),
(38,5,150),
(39,4,11),
(40,5,166),
(41,3,190),
(42,4,11),
(43,5,175),
(44,1,103),
(45,2,75),
(46,3,91),
(47,4,187),
(48,5,180),
(49,1,88),
(50,2,95),
(51,1,78),
(52,2,132),
(53,3,169),
(54,4,181),
(55,5,141),
(56,1,160),
(57,2,37),
(58,3,137),
(59,4,112),
(60,5,83),
(61,1,43),
(62,2,149),
(63,3,126),
(64,4,60),
(65,5,2),
(66,1,96),
(67,2,72),
(68,3,126),
(69,4,110),
(70,5,110),
(71,1,43),
(72,1,149),
(73,2,126),
(74,2,60),
(75,3,2),
(76,3,96),
(77,4,72),
(78,4,126),
(79,5,110),
(80,5,110),
(81,1,100),
(82,1,100),
(83,1,100),
(84,1,100),
(85,1,100),
(86,1,100),
(87,1,100),
(88,1,100),
(89,1,100),
(90,1,100),
(91,2,100),
(92,2,100),
(93,2,100),
(94,2,100),
(95,2,100),
(96,2,100),
(97,2,100),
(98,2,100),
(99,2,100),
(100,2,100),
(101,1,30),
(102,1,100),
(103,1,50),
(104,1,100),
(105,2,100),
(106,2,100),
(107,2,50),
(108,2,30),
(109,3,100),
(110,3,30),
(111,3,100),
(112,3,30),
(113,4,50),
(114,4,30),
(115,4,100),
(116,4,50),
(117,5,30),
(118,5,50),
(119,5,20),
(120,5,30);





create table subscription_records (
    record_id INT AUTO_INCREMENT PRIMARY KEY not null,
    user_id INT not null,
    sub_date date not null,
    product_id INT not null,
    quantity INT not null,
    sub_type ENUM('One-off', 'Weekly', 'Biweekly', 'Monthly') NOT NULL,
    payment_method_id INT not null,
    subscription_status ENUM('Active','Cancelled') not null,
	constraint foreign KEY (user_id) REFERENCES users(user_id),
	constraint foreign KEY (product_id) REFERENCES products(product_id),
	constraint foreign KEY (payment_method_id) REFERENCES payment_methods(payment_method_id)
    );





CREATE TABLE coupons (
    coupon_id INT AUTO_INCREMENT PRIMARY KEY,
    amount DECIMAL(10,2) NOT NULL,
    created_by int not null,
    depot_id int not null,
	constraint FOREIGN KEY (created_by) REFERENCES users(user_id)
);

CREATE TABLE scheduled_box (
    schedule_id INT NOT NULL AUTO_INCREMENT,
    product_id INT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    PRIMARY KEY (schedule_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);


create table return_authorization (
	form_id int auto_increment primary key,
    order_id int not null,
    applied_date datetime, 
	return_status enum ('pending', 'rejected', 'approved'),
    return_reason varchar(255),
	foreign key (order_id) REFERENCES orders(order_id)
    );
    
create table return_form (
	return_id int auto_increment primary key,
    form_id int not null,
    product_id int not null,
    return_quantity int,
    foreign key (form_id) REFERENCES return_authorization(form_id),
    foreign key (product_id) REFERENCES products(product_id)
)
    

