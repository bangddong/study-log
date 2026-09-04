---
emoji: "🚀"
title: "API 개발 고급 - 컬렉션 조회 최적화"
date: 2025-03-22 00:00:00
update: 2025-03-22 00:00:00
tags:
  - Spring
  - JPA
series: "스프링 부트와 JPA 활용 2"
---

주문 내역에서 추가로 주문한 상품 정보를 추가로 조회하는 기능을 추가 하겠습니다.   

Order 기준으로 컬렉션인 `OrderItem`과 `Item`이 필요한데 앞의 예제에는 OneToOne, ManyToOne 관계로 설정되어 있는데 이번엔 컬렉션인 OneToMany(일대다)를 조회하고 최적화 하는 방법도 같이 알아보겠습니다.

## 주문 조회 V1: 엔티티 직접 노출

### 주문조회

**OrderApiController**

```java
@RestController
@RequiredArgsConstructor
public class OrderApiController {

    private final OrderRepository orderRepository;

    @GetMapping("/api/v1/orders")
    public List<Order> ordersV1() {
        List<Order> all = orderRepository.findAllByString(new OrderSearch());
        for (Order order : all) {
            order.getMember().getName();
            order.getDelivery().getAddress();
            List<OrderItem> orderItems = order.getOrderItems();
            orderItems.forEach(o -> o.getItem().getName());
        }
        return all;
    }

}
```

- `orderItem`, `Item` 관계를 직접 초기화하면 `Hibernate5JakartaModule`설정에 의해 엔티티를 JSON으로 생성
- 양방향 연관관계면 무한 루프에 걸리지 않게 한곳에 `@JsonIgnore` 추가
- 엔티티를 직접 노출하므로 좋은 방법이 아님

## 주문 조회 V2: 엔티티를 DTO로 변환

**OrderApiController**

```java
@GetMapping("/api/v2/orders")
public List<OrderDto> ordersV2() {
    List<Order> orders = orderRepository.findAllByString(new OrderSearch());

return orders.stream()
	.map(OrderDto::new)
	.toList();
}

@Getter
static class OrderDto {
    private Long orderId;
    private String name;
    private LocalDateTime orderDate;
    private OrderStatus orderStatus;
    private Address address;
    private List<OrderItemDto> orderItems;

    public OrderDto(Order order) {
        orderId = order.getId();
        name = order.getMember().getName();
        orderDate = order.getOrderDate();
        orderStatus = order.getStatus();
        address = order.getDelivery().getAddress();
        orderItems = order.getOrderItems().stream()
            .map(OrderItemDto::new)
            .toList();
    }
}

@Getter
static class OrderItemDto {
    private String itemName;
    private int orderPrice;
    private int count;

    public OrderItemDto(OrderItem orderItem) {
        itemName = orderItem.getItem().getName();
        orderPrice = orderItem.getOrderPrice();
        count = orderItem.getCount();
    }
}
```

- 지연 로딩으로 너무 많은 SQL 실행
- SQL 실행 수
    - `order` 1번
    - `member`, `address` N번 (order 조회 수 만큼)
    - `orderItem` N번 (order 조회 수 만큼)
    - `item` N번 (orderItem 조회 수 만큼)

지연 로딩의 경우 영속성 컨텍스트에 없으면 SQL문을 그 때 실행하기 때문에 많은 쿼리가 발생하고 있습니다.

## 주문 조회 V3: 엔티티를 DTO로 변환 - 페치 조인 최적화

**OrderApiController - 추가**

```java
@GetMapping("/api/v3/orders")
public List<OrderDto> ordersV3() {
    List<Order> orders = orderRepository.findAllWithItem();

return orders.stream()
	.map(OrderDto::new)
	.toList();
}
```

**OrderRepository - 추가**

```java
public List<Order> findAllWithItem() {
	return em.createQuery(
		"select distinct o from Order o" +
			" join fetch o.member m" +
			" join fetch o.delivery d" +
			" join fetch o.orderItems oi" +
			" join fetch oi.item i", Order.class)
		.getResultList();
}
```

- 페치 조인으로 SQL 1번 실행
- `distinct`의 경우 hibernate 6 버전부터 자동으로 들어가기 때문에 없어도 자동으로 Order 중복 제거
- 컬렉션 둘 이상에 페치 조인을 사용하면 데이터가 부정합하게 조회될 수 있어 컬렉션 페치 조인은 1개만 사용할 수 있음
- 단점
    - 페이징 불가능

### 왜 페이징이 불가능해질까?

컬렉션 페지 조인시 hibernate에 의해 실행된 SQL을 보면 limit이나 offset 쿼리가 보이질 않습니다. `findAllWithItem` 메서드에 페이징 관련 메서드를 추가하면 다음과 같은 경고 메시지가 발생합니다.

```java
public List<Order> findAllWithItem() {
	return em.createQuery(
		"select distinct o from Order o" +
			" join fetch o.member m" +
			" join fetch o.delivery d" +
			" join fetch o.orderItems oi" +
			" join fetch oi.item i", Order.class)
		.setFirstResult(1) // 시작 row
		.setMaxResults(100) // 최대 row 수
		.getResultList();
}

// 쿼리 실행결과
select
    distinct o1_0.order_id,
    d1_0.delivery_id,
    d1_0.city,
    d1_0.street,
    d1_0.zipcode,
    d1_0.status,
    m1_0.member_id,
    m1_0.city,
    m1_0.street,
    m1_0.zipcode,
    m1_0.name,
    o1_0.order_date,
    oi1_0.order_id,
    oi1_0.order_item_id,
    oi1_0.count,
    i1_0.item_id,
    i1_0.dtype,
    i1_0.name,
    i1_0.price,
    i1_0.stock_quantity,
    i1_0.artist,
    i1_0.etc,
    i1_0.author,
    i1_0.isbn,
    i1_0.actor,
    i1_0.director,
    oi1_0.order_price,
    o1_0.status 
from
    orders o1_0 
join
    member m1_0 
        on m1_0.member_id=o1_0.member_id 
join
    delivery d1_0 
        on d1_0.delivery_id=o1_0.delivery_id 
join
    order_item oi1_0 
        on o1_0.order_id=oi1_0.order_id 
join
    item i1_0 
        on i1_0.item_id=oi1_0.item_id
```

`HHH90003004: firstResult/maxResults specified with collection fetch; applying in memory`

즉, DB에서 페이징 처리 된 데이터를 받아오는게 아닌 모든 데이터를 다 애플리케이션으로 받아온 이후 메모리에서 처리하겠다는 경고 메시지로 데이터가 조금만 많아도 엄청난 리소스를 잡아먹게 됩니다.

이는 hibernate가 데이터를 처리하는 방식에서 오는 문제점으로 애플리케이션에서 보면 정상적으로 두 개의 Order만 반환하고 있지만 위 쿼리를 그대로 DB에서 조회해보면 중복 그대로인 4개의 row가 출력되는 것을 볼 수 있습니다.

즉, DB 입장에선 4개의 row가 나오지만 JPA에서 기대하는건 중복이 제거된 2개의 `order`이기 때문에 일반적인 offset이나 limit으로는 처리가 불가능해지는 것입니다.

## 주문 조회 V3.1: 엔티티를 DTO로 변환 - 페이징과 한계 돌파

### 페이징과 한계 돌파

- 컬렉션을 페치 조인하면 페이징이 불가능
    - 컬렉션을 페치 조인하면 일대다 조인이 발생하므로 데이터가 예측할 수 없이 증가
    - 일다대에서 일(1)을 기준으로 페이징을 하는 것이 목적, 그런데 데이터는 다(N)를 기준으로 row가 생성됨
    - Order를 기준으로 페이징 하고 싶은데, 다(N0인 OrderItem을 조인하면 orderItem이 기준이 되어버림
- 이 경우 hibernate는 경고 로그를 남기고 모든 DB 데이터를 읽어서 메모리에서 페이징을 시도하며 최악의 경우 장애로 이어짐

### 한계 돌파

- 먼저 `ToOne`(OneToOne, ManyToOne) 관계를 모두 페치조인

  (ToOne 관계는 row 수를 증가 시키지 않으므로 페이징 쿼리에 영향 X)

- 컬렉션은 지연 로딩으로 조회
- 지연 로딩 성능 최적화를 위해 `hibernate.default_batch_fetch_size`, `@BatchSize`를 적용
    - hibernate.default_batch_fetch_size : 글로벌 설정
    - @BatchSize: 개별 최적화
    - 이 옵션을 사용하면 컬렉션이나, 프록시 객체를 한꺼번에 설정한 size만큼 IN 쿼리로 조회함

**OrderRepository - 추가**

```java
public List<Order> findAllWithMemberDelivery(int offset, int limit) {
	return em.createQuery(
		"select o from Order o" +
			" join fetch o.member m" +
			" join fetch o.delivery d", Order.class)
		.setFirstResult(offset)
		.setMaxResults(limit)
		.getResultList();
}
```

**OrderApiController - 추가**

```java
@GetMapping("/api/v3.1/orders")
public List<OrderDto> ordersV3_page(
    @RequestParam(value = "offset", defaultValue = "0") int offset,
    @RequestParam(value = "limit", defaultValue = "100") int limit
) {
    List<Order> orders = orderRepository.findAllWithMemberDelivery(offset, limit);

return orders.stream()
	.map(OrderDto::new)
	.toList();
}
```

**application.yml - 추가**

```java
spring:
	jpa:
	  properties:
	    hibernate:
	      default_batch_fetch_size: 100
```

- 개별로 설정하고 싶으면 `@BatchSize` 사용
- 장점
    - 쿼리 호출수가 `1 + N` ⇒ `1 + 1`로 최적화
    - 조인보다 DB 데이터 전송량이 최적화 됨 (Order와 OrderItem을 조인하면 Order가 OrderItem만큼 중복해서 조회하지만 이 방법은 각각 조회하므로 중복되지 않음)
    - 페치 조인 방식과 비교해서 쿼리 호출 수가 약간 증가하지만, DB 데이터 전송량이 감소
    - 컬렉션 페치 조인은 페이징이 불가능하지만 이 방법은 페이징 가능
- 결론
    - ToOne 관게는 페치 조인해도 페이징에 영향을 주지 않음. 따라서 ToOne 관계는 페치조인으로 쿼리 수를 줄이고, 나머지는 `hibernate.default_batch_fetch_size`로 최적화하면 됨
- default_batch_fetch_size 적절 사이즈
    - SQL IN 절을 사용하기 때문에 DB에 따라 In절 파라미터로 1000으로 제한하기도 함. 따라서 100 ~ 1000으로 설정하는 것이 가장 좋지만 DB든 애플리케이션이든 순간 부하를 견딜 수 있는 수준까지로 결정하면 됨

## 주문 조회 V4: JPA에서 DTO 직접 조회

**OrderApiController - 추가**

```java
@GetMapping("/api/v4/orders")
public List<OrderQueryDto> ordersV4() {
    return orderQueryRepository.findOrderQueryDtos();
}
```

**OrderQueryRepository (repository/order/query)**

```java
@Repository
@RequiredArgsConstructor
public class OrderQueryRepository {

	private final EntityManager em;

	public List<OrderQueryDto> findOrderQueryDtos() {
		List<OrderQueryDto> result = findOrders();
		result.forEach(o -> {
			List<OrderItemQueryDto> orderItems = findOrderItems(o.getOrderId());
			o.setOrderItems(orderItems);
		});

		return result;
	}

	private List<OrderItemQueryDto> findOrderItems(Long orderId) {
		return em.createQuery(
				"select new com.study.jpashop.repository.order.query.OrderItemQueryDto(oi.order.id, oi.item.name, oi.orderPrice, oi.count)"
					+ " from OrderItem oi"
					+ " join oi.item i"
					+ " where oi.order.id = :orderId", OrderItemQueryDto.class)
			.setParameter("orderId", orderId)
			.getResultList();
	}

	private List<OrderQueryDto> findOrders() {
		return em.createQuery(
				"select new com.study.jpashop.repository.order.query.OrderQueryDto(o.id, m.name, o.orderDate, o.status, d.address)"
					+ " from Order o"
					+ " join o.member m"
					+ " join o.delivery d", OrderQueryDto.class)
			.getResultList();
	}

}
```

**OrderItemQueryDto**

```java
@Data
public class OrderItemQueryDto {

	@JsonIgnore
	private Long orderId;
	private String itemName;
	private int orderPrice;
	private int count;

	public OrderItemQueryDto(Long orderId, String itemName, int orderPrice, int count) {
		this.orderId = orderId;
		this.itemName = itemName;
		this.orderPrice = orderPrice;
		this.count = count;
	}
}
```

**OrderItemQueryDto**

```java
@Data
public class OrderItemQueryDto {

	@JsonIgnore
	private Long orderId;
	private String itemName;
	private int orderPrice;
	private int count;

	public OrderItemQueryDto(Long orderId, String itemName, int orderPrice, int count) {
		this.orderId = orderId;
		this.itemName = itemName;
		this.orderPrice = orderPrice;
		this.count = count;
	}
}
```

- Query: 루트 1번, 컬렉션 N번 실행
- ToOne(N:1, 1:1) 관계들을 모두 조회하고, ToMany(1:N) 관계는 각각 별도로 처리
    - ToOne 관계는 조인해도 데이터 row 수가 증가하지 않음
    - ToMany (1:N) 관계는 조인하면 row 수 증가
- row 수가 증가하지 않는 ToOne 관계는 조인으로 최적화 하기 쉬우므로 한번에 조회하고, ToMany 관계는 최적화 하기 어려우므로 `findOrderItems()` 같은 별도의 메서드로 조회

## 주문 조회 V5: JPA에서 DTO 직접 조회 - 컬렉션 조회 최적화

**OrderApiController - 추가**

```java
@GetMapping("/api/v5/orders")
public List<OrderQueryDto> ordersV5() {
    return orderQueryRepository.findAllByDto_optimization();
}
```

**OrderQueryRepository - 추가**

```java
public List<OrderQueryDto> findAllByDto_optimization() {
	List<OrderQueryDto> result = findOrders();

	Map<Long, List<OrderItemQueryDto>> orderItemMap = findOrderItemMap(toOrderIds(result));

	result.forEach(o -> o.setOrderItems(orderItemMap.get(o.getOrderId())));

	return result;
}

private Map<Long, List<OrderItemQueryDto>> findOrderItemMap(List<Long> orderIds) {
	List<OrderItemQueryDto> orderItems = em.createQuery(
			"select new com.study.jpashop.repository.order.query.OrderItemQueryDto(oi.order.id, oi.item.name, oi.orderPrice, oi.count)"
				+ " from OrderItem oi"
				+ " join oi.item i"
				+ " where oi.order.id in :orderIds", OrderItemQueryDto.class)
		.setParameter("orderIds", orderIds)
		.getResultList();

	Map<Long, List<OrderItemQueryDto>> orderItemMap = orderItems.stream()
		.collect(Collectors.groupingBy(OrderItemQueryDto::getOrderId));
	return orderItemMap;
}

private static List<Long> toOrderIds(List<OrderQueryDto> result) {
	List<Long> orderIds = result.stream()
		.map(OrderQueryDto::getOrderId)
		.toList();
	return orderIds;
}
```

- Query: 루트 1번, 컬렉션 1번
- ToOne 관계들을 모두 조회하고, 여기서 얻은 식별자 orderId로 ToMany 관계인 `OrderItem`을 한꺼번에 조회
- Map을 사용해서 매칭 성능 향상(O(1))

## 주문 조회 V6: JPA에서 DTO로 직접 조회, 플랫 데이터 최적화

**OrderApiController - 추가**

```java
@GetMapping("/api/v6/orders")
public List<OrderQueryDto> ordersV6() {
    List<OrderFlatDto> flats = orderQueryRepository.findAllByDto_flat();

    return flats.stream()
        .collect(
            groupingBy(
                o -> new OrderQueryDto(
                    o.getOrderId(),
                    o.getName(),
                    o.getOrderDate(),
                    o.getOrderStatus(),
                    o.getAddress()
                ),
                Collectors.mapping(
                    o -> new OrderItemQueryDto(
                        o.getOrderId(),
                        o.getItemName(),
                        o.getOrderPrice(),
                        o.getCount()
                    ),
                    Collectors.toList()
                )
            )
        )
        .entrySet().stream()
        .map(e -> new OrderQueryDto(
            e.getKey().getOrderId(),
            e.getKey().getName(),
            e.getKey().getOrderDate(),
            e.getKey().getOrderStatus(),
            e.getKey().getAddress(),
            e.getValue()
        ))
        .toList();
}
```

**OrderQueryDto - 추가**

```java
public OrderQueryDto(
	Long orderId,
  String name,
  LocalDateTime orderDate, 
  OrderStatus orderStatus, 
  Address address,
	List<OrderItemQueryDto> orderItems
) {
	this.orderId = orderId;
	this.name = name;
	this.orderDate = orderDate;
	this.orderStatus = orderStatus;
	this.address = address;
	this.orderItems = orderItems;
}
```

**OrderQueryRepository - 추가**

```java
public List<OrderFlatDto> findAllByDto_flat() {
	return em.createQuery(
		"select new com.study.jpashop.repository.order.query.OrderFlatDto(o.id, m.name, o.orderDate, o.status, d.address, i.name, oi.orderPrice, oi.count)" +
			" from Order o" +
			" join o.member m" +
			" join o.delivery d" +
			" join o.orderItems oi" +
			" join oi.item i", OrderFlatDto.class)
		.getResultList();
}
```

**OrderFlatDto**

```java
@Data
public class OrderFlatDto {

	private Long orderId;
	private String name;
	private LocalDateTime orderDate;
	private OrderStatus orderStatus;
	private Address address;

	private String itemName;
	private int orderPrice;
	private int count;

	public OrderFlatDto(Long orderId, String name, LocalDateTime orderDate, OrderStatus orderStatus, Address address,
		String itemName, int orderPrice, int count) {
		this.orderId = orderId;
		this.name = name;
		this.orderDate = orderDate;
		this.orderStatus = orderStatus;
		this.address = address;
		this.itemName = itemName;
		this.orderPrice = orderPrice;
		this.count = count;
	}
}
```

- Query: 1번
- 단점
    - 쿼리는 한번이지만 조인으로 인해 DB에서 중복 데이터가 추가되니 상황에 따라 V5보다 느릴 수 있음
    - 애플리케이션에서 추가 작업이 많음
    - 페이징 불가능

## 컬렉션 조회 최적화 정리

### 엔티티 조회

- 엔티티를 조회해서 그대로 반환 : V1
- 엔티티 조회 후 DTO로 변환 : V2
- 페치 조인으로 쿼리 수 최적화 : V3
- 컬렉션 페이징과 한계 돌파: V3.1
    - 컬렉션은 페치 조인시 페이징 불가능
    - ToOne 관게는 페치 조인으로 쿼리 수 최적화
    - 컬렉션은 페치 조인 대신에 지연 로딩을 유지하고, `hibernate.default_batch_fetch_size, @BatchSize`로 최적화

### DTO 직접 조회

- JPA에서 DTO를 직접 조회: V4
- 컬렉션 조회 최적화
    - 일대다 관계인 컬렉션은 IN 절을 활용해서 메모리에서 미리 조회해서 최적화 : V5
- 플랫 데이터 최적화
    - JOIN 결과를 그대로 조회 후 애플리케이션에서 원하는 모양으로 직접 변환 : V6

### 권장 순서

1. 엔티티 조회 방식으로 우선 접근
    1. 페치조인으로 쿼리 수를 최적화
    2. 컬렉션 최적화
        1. 페이징 필요 `hibernate.default_batch_fetch_size, @BatchSize`로 최적화
        2. 페이징 필요 X ⇒ 페치 조인 사용
2. 엔티티 조회 방식으로 해결이 안되면 DTO 조회 방식 사용
3. DTO 조회 방식으로 해결이 안되면 NativeSQL or 스프링 JdbcTemplate 사용

엔티티 조회 방식은 페이 조인이나, `hibernate.default_batch_fetch_size, @BatchSize` 같이 코드를 거의 수정하지 않고, 옵션만 약간 변경해서, 다양한 성능 최적화를 시도할 수 있습니다. 반면에 DTO를 직접 조회하는 방식은 성능을 최적화 하거나 성능 최적화 방식을 변경할 때 많은 코드를 변경해야 합니다.

따라서 개발자는 성능 최적화와 코드 복잡도 사이에서 줄타기를 잘 해야 합니다. 항상 그런 것은 아니지만, 보통 성능 최적화는 **단순한 코드를 복잡한 코드로 몰고갑니다.**

엔티티 조회 방식은 **JPA가 많은 부분을 최적화** 해주기 때문에, 단순한 코드를 유지하면서, 성능을 최적화 할 수 있습니다.

반면 DTO 조회 방식은 **SQL을 직접 다루는 것**과 유사하기 때문에, 둘 사이에서 상황에 따라 줄타기를 해야 합니다.

### DTO 조회 방식의 선택지

- DTO로 조회하는 방법도 각각 장단이 있다. V4, V5, V6에서 단순하게 쿼리가 1번 실행된다고 V6가 항상 좋은 방법인 것은 아니다.
- V4는 코드가 단순하다. 특정 주문 한건만 조회하면 이 방식을 사용해도 성능이 잘 나온다. 예를 들어 조회한 Order 데이터가 1건이면 OrderItem을 찾기 위한 쿼리도 1번만 실행하면 된다.
- V5는 코드가 복잡하다. 여러 주문을 한꺼번에 조회하는 경우에도 V4 대신에 이것을 최적화한 V5 방식을 사용해야 한다. 예를 들어 조회한 Order 데이터가 1000건인데, V4 방식을 그대로 사용하면, 쿼리가 총 1 + 1000번 실행된다. 여기서 1은 Order를 조회한 쿼리이고, 1000은 조회된 Order의 row 수다. V5 방식으로 최적화 하면 쿼리가 총 1 + 1번만 실행된다. 상황에 따라 다르겠지만 운영 환경에서 100배 이상의 성능 차이가 날 수 있다.
- V6는 완전히 다른 접근방식이다. 쿼리 한번으로 최적화 되어서 상당히 좋아보이지만, Order를 기준으로 페이징이 불가능하다. 실무에서는 이정도 데이터면 수백이나, 수천건 단위로 페이징 처리가 꼭 필요하므로, 이 경우 선택하기 어려운 방법이다. 그리고 데이터가 많으면 중복 전송이 증가해서 V5와 비교해서 성능 차이도 미비하다

**이 링크를 통해 구매하시면 제가 수익을 받을 수 있어요. 🤗**

https://inf.run/4Sbno