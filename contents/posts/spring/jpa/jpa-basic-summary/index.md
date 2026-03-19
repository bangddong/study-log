---
emoji: "🚀"
title: "JPA 기본 최종정리"
date: 2025-03-12 00:00:00
update: 2025-03-12 00:00:00
tags:
  - Spring
  - JPA
series: "JPA 기본"
---

## **1. JPA 개요**

- JPA(Java Persistence API)는 객체와 관계형 데이터베이스 간 **패러다임 불일치 문제**를 해결하기 위해 등장.
- SQL 중심 개발을 **객체 중심 개발**로 전환하여 **생산성 향상**.
- 주요 구현체: **Hibernate**, EclipseLink, OpenJPA 등.

---

## **2. 영속성 컨텍스트 (Persistence Context)**

- **JPA에서 가장 중요한 개념!**
- **`EntityManager`**가 관리하는 **1차 캐시** 역할.
- 같은 트랜잭션 내에서 동일한 엔티티는 동일한 객체로 관리됨.
- 주요 동작:
    - **`persist()`**: 영속 상태로 변경
    - **`find()`**: 1차 캐시에서 조회 (없으면 DB 조회 후 캐싱)
    - **`remove()`**: 삭제 처리
    - **`merge()`**: 준영속 상태 객체를 영속 상태로 변경

---

## **3. 엔티티 생명주기**

1. **비영속 (Transient)** → **`new`**로 생성했지만 아직 JPA가 관리하지 않는 상태.
2. **영속 (Managed)** → **`persist()`**를 호출하면 영속성 컨텍스트에서 관리됨.
3. **준영속 (Detached)** → **`detach()`** 호출하거나 **`clear()`**, **`close()`** 하면 관리 대상에서 제외됨.
4. **삭제 (Removed)** → **`remove()`** 호출 시 DB에서 삭제됨.

---

## **4. 기본 매핑**

- **`@Entity`**: JPA에서 엔티티로 사용.
- **`@Id`**: 기본 키(primary key) 설정.
- **`@GeneratedValue`**: 자동 생성 전략.
    - **`IDENTITY`**: DB가 자동 생성 (AUTO_INCREMENT)
    - **`SEQUENCE`**: DB 시퀀스 사용 (Oracle 등)
    - **`TABLE`**: 키 생성 전용 테이블 사용
    - **`AUTO`**: DB에 따라 자동 선택
- **`@Column(name="칼럼명")`**: 필드와 DB 컬럼 매핑.

---

## **5. 연관관계 매핑**

JPA에서는 객체 간 연관관계를 **외래 키가 아닌 객체 자체로** 표현해야 함.

### **✅ 연관관계 종류**

1. **단방향 관계**
    - **`@ManyToOne`**: 다대일 관계 (N:1)
    - **`@OneToOne`**: 일대일 관계 (1:1)
2. **양방향 관계**
    - **`@OneToMany`**: 일대다 관계 (1:N)
    - **`@ManyToMany`**: 다대다 관계 (연결 테이블 필요)

### **✅ 연관관계 설정 시 주의할 점**

- **연관관계의 주인(owner)을 명확히 해야 함.**
- **`@ManyToOne`**이 주인이고, **`@OneToMany`**는 **`mappedBy`**를 사용해 연관관계를 설정.

```java
@Entity
class Member {
    @Id @GeneratedValue
    private Long id;

    @ManyToOne
    @JoinColumn(name = "team_id") // 외래키
    private Team team;
}

@Entity
class Team {
    @Id @GeneratedValue
    private Long id;

    @OneToMany(mappedBy = "team") // 읽기 전용
    private List<Member> members = new ArrayList<>();
}

```

---

## **6. 프록시와 지연 로딩**

- JPA는 엔티티를 바로 조회하지 않고, 필요할 때 실제 데이터를 가져오는 **지연 로딩(LAZY Loading)**을 지원.
- **즉시 로딩(EAGER) 사용 시 성능 문제 발생 가능.**
- **`@OneToMany`**, **`@ManyToMany`** 기본값: **LAZY**
- **`@ManyToOne`**, **`@OneToOne`** 기본값: **EAGER**

```java
@ManyToOne(fetch = FetchType.LAZY)
private Team team;
```

⚠ **즉시 로딩(EAGER)은 지양하고, 필요할 때 `fetch join`이나 `EntityGraph`를 활용하자!**

---

## **7. JPQL과 QueryDSL**

JPA는 **JPQL (Java Persistence Query Language)**을 제공하여 SQL을 객체 중심으로 변환.

### **✅ JPQL 기본 문법**

- SQL과 유사하지만 **테이블이 아닌 엔티티(Member)를 대상으로 쿼리**.
- **`JOIN FETCH`** 사용 시 연관된 엔티티도 한 번에 조회 가능.

```sql
SELECT m FROM Member m JOIN FETCH m.team
```

⚡ **QueryDSL을 활용하면 타입 안전한 쿼리 작성 가능.**

```java
JPAQueryFactory queryFactory = new JPAQueryFactory(entityManager);
QMember m = QMember.member;
List<Member> members = queryFactory.selectFrom(m)
                                   .where(m.age.gt(18))
                                   .fetch();
```

---

## **8. 트랜잭션과 변경 감지 (Dirty Checking)**

- JPA는 엔티티 변경 시 자동으로 업데이트 SQL 실행.
- **트랜잭션 내에서 엔티티 값을 변경하면 `flush()` 시점에 SQL이 자동 실행됨.**

```java
@Transactional
public void updateMember(Long id) {
    Member member = em.find(Member.class, id);
    member.setName("변경됨"); // UPDATE SQL 실행됨 (Dirty Checking)
}
```

⚠ **트랜잭션이 없으면 변경 사항이 반영되지 않으니 주의!**

---

## **9. N+1 문제와 해결 방법**

- 연관된 엔티티를 **`LAZY`** 로딩할 때, 추가적인 쿼리가 반복 실행되는 문제.
- 예제: 회원을 조회할 때 **`team`**을 **`Lazy`**로딩하면, 회원 개수만큼 **`SELECT`** 쿼리가 실행됨.

### **✅ 해결 방법**

1. **Fetch Join** 사용 (즉시 로딩처럼 한 번에 조회)

    ```sql
    SELECT m FROM Member m JOIN FETCH m.team
    ```

2. **EntityGraph 사용**

    ```java
    @EntityGraph(attributePaths = {"team"})
    @Query("SELECT m FROM Member m")
    List<Member> findAllWithTeam();
    ```

3. **Batch Size 설정 (`hibernate.default_batch_fetch_size`)**→ 한 번의 SQL로 여러 개의 **`team`** 데이터를 가져옴.

    ```
    spring.jpa.properties.hibernate.default_batch_fetch_size=100
    ```


---

## **10. 실무에서 주의할 점**

- **즉시 로딩(EAGER)은 피하고, 지연 로딩(LAZY)과 `fetch join`을 적절히 사용하자.**
- **JPA에서 엔티티 ID만 필요하면 조회 성능 최적화를 위해 DTO를 사용하자.**
- **N+1 문제는 Fetch Join, EntityGraph, Batch Size 등을 활용해 해결하자.**
- **연관관계 매핑 시 양방향 관계를 신중하게 설계하고, `mappedBy` 설정을 올바르게 하자.**
- **Dirty Checking을 활용해 엔티티 변경을 자동 반영하도록 설계하자.**

---

## **결론**

- JPA는 **객체 중심 개발**을 가능하게 하지만, **올바른 사용법을 익히지 않으면 성능 문제가 발생할 수 있음.**
- 실무에서는 **연관관계 설정, JPQL 최적화, 트랜잭션 관리, N+1 문제 해결**이 핵심.
- **무조건 JPA를 사용하기보다는, 상황에 따라 Native Query, QueryDSL도 함께 활용하자!**

**이 링크를 통해 구매하시면 제가 수익을 받을 수 있어요. 🤗**

https://inf.run/4Sbno