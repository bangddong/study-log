---
emoji: "🚀"
title: "API 개발 기본"
date: 2025-03-19 00:00:00
update: 2025-03-19 00:00:00
tags:
  - Spring
  - JPA
series: "스프링 부트와 JPA 활용 2"
---

## 애플리케이션 기동시 샘플 데이터 init

### InitDb

```java
/**
 * 종 주문 2개
 * * userA
 * 	 * JPA1 BOOK
 * 	 * JPA2 BOOK
 * * userB
 * 	 * SPRING1 BOOK
 * 	 * SPRING2 BOOK
 */
@Component
@RequiredArgsConstructor
public class InitDb {

	private final InitService initService;

	@PostConstruct
	public void init() {
		initService.dbInit1();
		initService.dbInit2();
	}

	@Component
	@Transactional
	@RequiredArgsConstructor
	static class InitService {

		private final EntityManager em;

		public void dbInit1() {
			System.out.println("Init1" + this.getClass());
			Member member = createMember("userA", "서울", "1", "1111");
			em.persist(member);

			Book book1 = createBook("JPA1 BOOK", 10000, 100);
			em.persist(book1);

			Book book2 = createBook("JPA2 BOOK", 20000, 100);
			em.persist(book2);

			OrderItem orderItem1 = OrderItem.createOrderItem(book1, 10000, 1);
			OrderItem orderItem2 = OrderItem.createOrderItem(book2, 20000, 2);

			Delivery delivery = createDelivery(member);
			Order order = Order.createOrder(member, delivery, orderItem1, orderItem2);
			em.persist(order);
		}

		public void dbInit2() {
			Member member = createMember("userB", "진주", "2", "2222");
			em.persist(member);

			Book book1 = createBook("SPRING1 BOOK", 20000, 200);
			em.persist(book1);

			Book book2 = createBook("SPRING2 BOOK", 40000, 300);
			em.persist(book2);

			OrderItem orderItem1 = OrderItem.createOrderItem(book1, 20000, 3);
			OrderItem orderItem2 = OrderItem.createOrderItem(book2, 40000, 4);

			Delivery delivery = createDelivery(member);
			Order order = Order.createOrder(member, delivery, orderItem1, orderItem2);
			em.persist(order);
		}

		private Member createMember(String name, String city, String street, String zipcode) {
			Member member = new Member();
			member.setName(name);
			member.setAddress(new Address(city, street, zipcode));
			return member;
		}

		private Book createBook(String name, int price, int stockQuantity) {
			Book book1 = new Book();
			book1.setName(name);
			book1.setPrice(price);
			book1.setStockQuantity(stockQuantity);
			return book1;
		}

		private Delivery createDelivery(Member member) {
			Delivery delivery = new Delivery();
			delivery.setAddress(member.getAddress());
			return delivery;
		}
	}
}
```

**이 링크를 통해 구매하시면 제가 수익을 받을 수 있어요. 🤗**

https://inf.run/4Sbno