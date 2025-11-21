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

주문 + 배송정보 + 회원을 조회하는 API를 만들 예정이며 지연 로딩 때문에 발생하는 성능 문제를 단계적으로 해결합니다.

## V1: 엔티티를 직접 노출

### 주문조회

**OrderSimpleApiController**

```java
/**
* xToOne(ManyToOne, OneToOne) 관계 최적화
* Order
* Order -> Member
* Order -> Delivery
*/
@RestController
@RequiredArgsConstructor
public class OrderSimpleApiController {

	private final OrderRepository orderRepository;
	
	@GetMapping("/api/v1/simple-orders")
	public List<Order> ordersV1() {
		List<Order> all = orderRepository.findAllByString(new OrderSearch());
		for (Order order : all) {
			order.getMember().getName(); // Lazy 강제 초기화
			order.getDelivery().getAddress(); // Lazy 강제 초기화
		}
		return all;
	}

}
```

- 엔티티를 직접 노출하는 것은 좋지 않음 (앞에서 설명)
- `order` → `member`와 `order` → `delivery`는 지연 로딩. 실제 엔티티 대신 프록시 존재
- jackson 라이브러리는 기본적으로 이 프록시 객체를 json으로 어떻게 생성해야 하는지 모르기에 예외 발생
- `Hibernate5JakartaModule`을 스프링 빈으로 등록하면 해결(스프링 부트 사용)

### 하이버네이트 모듈 등록 방법

**build.gradle**

```java
implementation 'com.fasterxml.jackson.datatype:jackson-datatype-hibernate5-jakarta'
```

**JpashopApplication**

```java
@Bean
Hibernate5JakartaModule hibernate5Module() {
	return new Hibernate5JakartaModule();
}
```

- 해당 Bean 추가시 초기화 된 프록시 객체만 노출하고 초기화 되지 않은 프록시 객체는 노출 안함

### 주의사항

- 엔티티를 직접 노출할 때는 양방향 연관관계가 걸린 곳은 꼭! 한 곳을 @JsonIgnore 처리를 해야 순환참조 문제를 피할 수 있음
- 지연 로딩(LAZY)를 피하기 위해 즉시 로딩(EAGER)으로 설정하면 안됨. 즉시 로딩 때문에 연관관계가 필요 없는 경우에도 데이터를 항상 조회해서 성능 문제가 발생할 수 있음. 항상 지연 로딩을 기본으로 하고, 성능 최적화가 필요한 경우에는 페치 조인을 꼭 사용해야 함
- 계속 언급했듯 엔티티 직접 노출은 피하고 DTO로 변환해서 쓰자!

## V2: 엔티티를 DTO로 변환

**OrderSimpleApiController**

```java
@GetMapping("/api/v2/simple-orders")
public List<SimpleOrderDto> ordersV2() {
	List<Order> orders = orderRepository.findAllByString(new OrderSearch());

	return orders.stream()
		.map(SimpleOrderDto::new)
		.toList();
}

@Data
static class SimpleOrderDto {
	private Long orderId;
	private String name;
	private LocalDateTime orderDate;
	private OrderStatus orderStatus;
	private Address address;

	public SimpleOrderDto(Order order) {
		orderId = order.getId();
		name = order.getMember().getName(); // Lazy 초기화
		orderDate = order.getOrderDate();
		orderStatus = order.getStatus();
		address = order.getDelivery().getAddress(); // Lazy 초기화
	}
}
```

- 엔티티를 DTO로 변환하는 일반적인 방법
- 쿼리가 총 1 + N + N번 실행 (v1과 쿼리수가 같음)
    - `order` 조회 1번(order 조회 결과 수가 N)
    - `order` → `member` 지연 로딩 조회 N번
    - `order` → `delivery` 지연 로딩 조회 N번
    - 예) order의 결과가 2개면 최악의 경우 1 + 2 + 2번 실행됨
        - 지연 로딩은 영속성 컨텍스트에서 조회하므로, 이미 조회된 경우 쿼리를 생략

## V3: 엔티티를 DTO로 변환 - 페치 조인 최적화

**OrderSimpleApiController - 추가**

```java
@GetMapping("/api/v3/simple-orders")
public List<SimpleOrderDto> ordersV3() {
	List<Order> orders = orderRepository.findAllWithMemberDelivery();
	
	return orders.stream()
		.map(SimpleOrderDto::new)
		.toList();
}
```

**OrderRepository - 추가**

```java
public List<Order> findAllWithMemberDelivery() {
	return em.createQuery(
		"select o from Order o" +
			" join fetch o.member m" +
			" join fetch o.delivery d", Order.class
	).getResultList();
}
```

- 엔티티를 페치 조인(fetch join)을 사용해서 쿼리 1번에 조회
- 페치 조인으로 `roder` → `member`, `order` → `delivery`는 이미 조회 된 상태 이므로 지연로딩 X

## V4: JPA에서 DTO로 바로 조회

**OrderSimpleApiController - 추가**

```java
// 의존성 추가
private final OrderSimpleQueryRepository orderSimpleQueryRepository;

@GetMapping("/api/v4/simple-orders")
public List<SimpleOrderDto> ordersV4() {
	return orderRepository.findOrderDtos();
}
```

**OrderSimpleQueryRepository - 조회 전용 리포지토리**

```java
@Repository
@RequiredArgsConstructor
public class OrderSimpleQueryRepository {

	private final EntityManager em;

	public List<OrderSimpleQueryDto> findOrderDtos() {
		return em.createQuery(
			"select new com.study.jpashop.repository.OrderSimpleQueryDto(o.id, m.name, o.orderDate, o.status, d.address)" +
				" from Order o" +
				" join o.member m" +
				" join o.delivery d", OrderSimpleQueryDto.class
		).getResultList();
	}
}
```

**OrderSimpleQueryDto**

```java
@Data
public class OrderSimpleQueryDto {
	private Long orderId;
	private String name;
	private LocalDateTime orderDate;
	private OrderStatus orderStatus;
	private Address address;

	public OrderSimpleQueryDto(
		Long orderId,
		String name,
		LocalDateTime orderDate,
		OrderStatus orderStatus,
		Address address
	) {
		this.orderId = orderId;
		this.name = name;
		this.orderDate = orderDate;
		this.orderStatus = orderStatus;
		this.address = address;
	}
}
```

- 일반적인 SQL을 사용할 때 처럼 원하는 값을 선택하여 조회
- `new` 명령어를 사용해서 JPQL의 결과를 DTO로 즉시 변환
- SELECT 절에서 원하는 데이터를 직접 선택하므로 DB → 애플리케이션 네트웍 용량 최적화(생각보다 미미)
- 리포지토리 재사용성 떨어짐, API 스펙에 맞춘 코드가 리포지토리에 들어가는 단점

## 정리

엔티티를 DTO로 변환하거나, DTO로 바로 조회하는 두 가지 방법은 각각 장단점이 있습니다. 둘 중 상황에 따라서 더 나은 방법을 선택하면 됩니다. 엔티티로 조회하면 리포지토리 재사용성도 좋고, 개발도 단순해지기 때문에 권장하는 방법은 다음과 같습니다.

### 쿼리 방식 선택 권장 순서

1. 우선 엔티티를 DTO로 변환하는 방법을 선택한다.
2. 필요하다면 페치 조인으로 성능을 최적화 한다. → 대부분의 성능 이슈가 해결된다.
3. 그래도 안되면 DTO로 직접 조회하는 방법을 사용한다.
4. 최후의 방법은 JPA가 제공하는 네이티브 SQL이나 스프링 JDBC Template을 사용해서 SQL을 직접 사용한다.

**이 링크를 통해 구매하시면 제가 수익을 받을 수 있어요. 🤗**

https://inf.run/4Sbno