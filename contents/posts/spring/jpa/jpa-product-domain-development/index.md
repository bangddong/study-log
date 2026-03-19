---
emoji: "🚀"
title: "상품 도메인 개발"
date: 2025-03-18 13:55:00
update: 2025-03-18 13:55:00
tags:
  - Spring
  - JPA
series: "스프링 부트와 JPA 활용 1"
---

## 상품 엔티티 개발(비즈니스 로직 추가)

### Item

```java
@Entity
@Inheritance(strategy = InheritanceType.SINGLE_TABLE)
@DiscriminatorColumn(name = "dtype")
@Getter
@Setter
public abstract class Item {

	@Id
	@GeneratedValue
	@Column(name = "item_id")
	private Long id;

	private String name;

	private int price;

	private int stockQuantity;

	@ManyToMany(mappedBy = "items")
	private List<Category> categories = new ArrayList<>();
	
	// 비즈니스 로직
	
	/**
	 * stock 증가
	 */
	public void addStock(int quantity) {
		this.stockQuantity += quantity;
	}
	
	/**
	 * stock 감소
	 */
	public void removeStock(int quantity) {
		int restStock = this.stockQuantity - quantity;
		if (restStock < 0) {
			throw new NotEnoughStockException("need more stock");
		}
		this.stockQuantity = restStock;
	}
	
}
```

### NotEnoughStockException

```java
public class NotEnoughStockException extends RuntimeException {

	public NotEnoughStockException() {
		super();
	}

	public NotEnoughStockException(String message) {
		super(message);
	}

	public NotEnoughStockException(String message, Throwable cause) {
		super(message, cause);
	}

	public NotEnoughStockException(Throwable cause) {
		super(cause);
	}

}
```

**비즈니스 로직**

- addStock(): 파라미터로 넘어온 수만큼 재고 증가
- removeStock(): 파라미터로 넘어온 수만큼 재고 감소

### ItemRepository

```java
@Repository
@RequiredArgsConstructor
public class ItemRepository {

	private final EntityManager em;

	public void save(Item item) {
		if (item.getId() == null) {
			em.persist(item);
		} else {
			em.merge(item);
		}
	}

	public Item findOne(Long id) {
		return em.find(Item.class, id);
	}

	public List<Item> findAll() {
		return em.createQuery("select i from Item i", Item.class)
			.getResultList();
	}
	
}
```

**기능**

- save()
    - id가 없으면 신규로 보고 `persist()` 실행
    - id가 있으면 이미 DB에 저장된 엔티티를 수정한다고 보고, `merge()`를 실행

## 상품 서비스 개발

### ItemService

```java
@Service
@Transactional(readOnly = true)
@RequiredArgsConstructor
public class ItemService {
	
	private final ItemRepository itemRepository;
	
	@Transactional
	public void saveItem(Item item) {
		itemRepository.save(item);
	}
	
	public Item findItem(Long itemId) {
		return itemRepository.findOne(itemId);
	}
	
	public List<Item> findItems() {
		return itemRepository.findAll();
	}
	
}
```

**이 링크를 통해 구매하시면 제가 수익을 받을 수 있어요. 🤗**

https://inf.run/4Sbno