---
emoji: "🚀"
title: "다양한 쿼리 문법"
date: 2025-03-12 00:00:00
update: 2025-03-12 00:00:00
tags:
  - Spring
  - JPA
series: "JPA 기본"
---

![image.png](images/img.png)

## 다형성 쿼리

조회 대상을 특정 자식으로 한정하는 기능입니다.

예) Item 중 Book, Movie 조회

```java
// JPQL
slect i from Item i
where **type(i)** IN (Book, Movie)

// SQL
select i from i
where i.DTYPE in ('B', 'M')
```

### TREAT

자바의 타입 캐스팅과 유사하며 상속 구조에서 부모 타입을 특저 ㅇ자식 타입으로 다룰 때 사용합니다.

예) 부모인 Item과 자식 Book이 있음.

```java
// JPQL
select i from Item i
where **treat(i as Book)**.author = 'kim'

// SQL
select i.* from Item i
where i.DTYPE = 'B' and i.author = 'kim'
```

## 엔티티 직접 사용

JPQL에서 엔티티 필드가 아닌 엔티티를 직접 사용하면 SQL에서 해당 엔티티의 기본 키 값을 사용하게 됩니다.

```java
// JPQL
select count(m.id) from Member m // 엔티티의 아이디를 사용
select count(m) from Member m // 엔티티를 직접 사용

// sql (jqpl 둘 다 같은 다음 SQL 실행)
select count(m.id) as cnt from Member m
```

## Named 쿼리(정적 쿼리)
JPQL에서 미리 정의해서 이름을 부여해두고 사용하는 방법으로 어노테이션이나 XML에 정의해서 `어플리케이션 로딩 시점`에 초기화 후 재사용하기 때문에 `해당 시점에 쿼리를 검증`합니다.

### 어노테이션 방식

```java
@Entity
@NamedQuery(
        name = "Member.findByUsername",
        query="select m from Member m where m.username = :username")
 public class Member {
    ...
 }
 
List<Member> resultList = 
em.createNamedQuery("Member.findByUsername", Member.class) // 미리 정의한 쿼리 실행
      .setParameter("username", "회원1")
      .getResultList();
```

### XML 방식

```java
// persistence.xml
<persistence-unit name="jpabook" >
	<mapping-file>META-INF/ormMember.xml</mapping-file>
	
// ormMember.xml
<?xml version="1.0" encoding="UTF-8"?>
 <entity-mappings xmlns="http://xmlns.jcp.org/xml/ns/persistence/orm" version="2.1">
    <named-query name="Member.findByUsername">
        <query><![CDATA[
            select m
            from Member m
            where m.username = :username
        ]]></query>
    </named-query>
    <named-query name="Member.count">
        <query>select count(m) from Member m</query>
    </named-query>
 </entity-mappings>
```

어노테이션과 XML 동시 사용시 항상 XML이 우선권을 가지며 운영 환경에 따라 다른 XML을 배포할 수 있습니다. 따로 선언해서 사용하는게 불편할 수는 있지만 `JpaRepository내 @Query를 통해 사용하는 모든 쿼리는 이름 없는 named 쿼리로 등록`되어 사용됩니다.

## 벌크 연산

벌크 연산이란 일반적으로 생각하는 SQL 내 update나 delete 쿼리로 생각하면 되는데 이해를 위한 시나리오는 다음과 같습니다.

- 재고가 10개 미만인 모든 상품의 가격을 10% 상승하려면?
- JPA 변경 감지 기능으로 실행하려면 너무 많은 SQL이 실행된다.
    1. 재고가 10개 미만인 상품을 리스트로 조회
    2. 상품 엔티티의 가격을 10% 증가
    3. 트랜잭션 커밋 시점에 변경감지가 동작 (더티체킹)
- 변경된 데이터가 100건이라면? ⇒ 100번의 UPDATE SQL 실행

### 벌크 연산 예제

쿼리 한 번으로 여러 테이블 로우를 변경하는 기능을 JPA는 제공합니다. (엔티티 기준)

```java
String qlString = "update Product p " + 
                  "set p.price = p.price * 1.1 " +  
                  "where p.stockAmount < :stockAmount";  

// excuteUpdate의 return 값은 "영향받은 엔티티의 수"
int resultCount = em.createQuery(qlString) 
                    .setParameter("stockAmount", 10)  
                    .executeUpdate();  
```

### 벌크 연산 주의사항

벌크 연산은 영속성 컨텍스트를 무시하고 직접 쿼리하기 때문에 꼭 벌크 연산을 `먼저 수행`하거나, 연산 수행 후 `영속성 컨텍스트를 초기화`해줘야 합니다.

```java
// Member 1~3은 영속화만 되어 있고 DB에는 없음
Member member1 = new Member();
member1.setUsername("회원1");
member1.setAge(0);
member1.setTeam(teamA);
em.persist(member1);

Member member2 = new Member();
member2.setUsername("회원2");
member2.setAge(0);
member2.setTeam(teamA);
em.persist(member2);

Member member3 = new Member();
member3.setUsername("회원3");
member3.setAge(0);
member3.setTeam(teamB);
em.persist(member3);

// 벌크 연산은 "DB에 직접" 쿼리하기 때문에 update 쿼리가 나가도 반영되지 않음
int resultCount = em.createQuery("update Member m set m.age = 20")
    .executeUpdate();

Member findMember = em.find(Member.class, member1.getId());

System.out.println("findMember = " + findMember.getAge());

// 실행 결과
Hibernate: 
    /* update
        Member m 
    set
        m.age = 20 */ update Member 
    set
        age=20
findMember = 0

==========================================================================
// 벌크 연산 수행 후 영속성 초기화
...
int resultCount = em.createQuery("update Member m set m.age = 20")
    .executeUpdate();
    
em.clear();

Member findMember = em.find(Member.class, member1.getId());

System.out.println("findMember = " + findMember.getAge());

// 실행 결과
Hibernate: 
    /* update
        Member m 
    set
        m.age = 20 */ update Member 
    set
        age=20
Hibernate: 
    select
        m1_0.id,
        m1_0.age,
        m1_0.TEAM_ID,
        m1_0.username 
    from
        Member m1_0 
    where
        m1_0.id=?
findMember = 20
```

**이 링크를 통해 구매하시면 제가 수익을 받을 수 있어요. 🤗**

https://inf.run/4Sbno