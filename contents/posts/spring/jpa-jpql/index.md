---
emoji: "🚀"
title: "객체지향 쿼리 언어(JPQL)"
date: 2025-02-27 00:00:00
update: 2025-02-27 00:00:00
tags:
  - Spring
  - JPA
series: "JPA 기본"
---

## JPA의 다양한 쿼리 방법

여러가지 특정 조건에서 데이터를 조회하려면 결국은 복잡하고 다양한 실제 SQL이 실행되어야 하는데 JPA는 아래와 같은 다양한 쿼리 방법을 지원합니다.

- JPQL
- JPA Criteria
- QueryDSL
- 네이티브 SQL
- JDBC API 직접 사용 (MyBatis, SpringJdbcTemplate)

### JPQL

가장 단순한 조회 방법은 예제로 사용하던 EntityManager를 통한 방법이었습니다.

- EntityManager.find()
- 객체 그래프 탐색(a.getB().getC())

JPA를 사용하면 엔티티 객체를 중심으로 개발하게 되는데 검색을 할 때에도 **테이블이 아닌 `엔티티 객체를 대상으로 검색`**해야 합니다. 모든 DB 데이터를 객체로 변환해서 검색하는 것은 불가능하니 어플리케이션이 필요한 데이터만 불러오려면 결국은 **검색 조건이 포함된 SQL을 사용**해야 합니다.

JPA는 검색 조건 SQL을 지원하기 위해 SQL을 추상화한 JPQL이라는 객체 지향 쿼리 언어를 제공합니다. 기본적으로 SQL과 문법이 유사하며 SELECT, FROM, WHERE, GROUp BY, HAVING, JOIN과 같은 표준 문법을 모두 지원합니다. 즉 JPQL은 엔티티 객체를 대상으로 쿼리하는 것이고 SQL은 DB 테이블을 대상으로 쿼리합니다.

간단하게 JPQL로 이름에 hello를 like 검색하는 코드입니다.

```java
String jpql = "select m From Member m where m.name like '%hello%'";
List<Member> result = em.createQuery(jpql, Member.class).getResultList();

Hibernate: 
    /* select
        m 
    From
        Member m 
    where
        m.username like '%hello%' */ select
            m1_0.MEMBER_ID,
            m1_0.city,
            m1_0.street,
            m1_0.zipcode,
            m1_0.USERNAME 
        from
            Member m1_0 
        where
            m1_0.USERNAME like '%hello%' escape ''
```

JPQL은 객체 지향 쿼리이기 때문에 위 코드에서 select하는 Member는 **테이블이 아닌 객체**이며 SQL을 추상화 했기 때문에 **`특정 DB에 의존하지 않는다`**는 특징을 갖고 있습니다.

하지만 위와 같이 쓰면 jpql 역시 단순 String 문자열이기 떄문에 **`동적 쿼리`**를 만들기가 굉장히 어렵고 번거로워 집니다.

```java
String jpql = "select m From Member m ";

if (userName != null) {
	String where = "where m.name like '%hello%'";
	jpql += where;
}
...
// AND? OR??...

List<Member> result = em.createQuery(jpql, Member.class).getResultList();
```

### Criteria

단순 문자열로 JPQL을 작성하기 힘드니 문자가 아닌 자바 코드로 JPQL을 작성할 수 있는 라이브러리입니다. JPA에서 공식적으로 지원하는 기능이며 JPQL 빌더와 같은 역할을 수행합니다.

```java
CriteriaBuilder cb = em.getCriteriaBuilder();
CriteriaQuery<Member> query = cb.createQuery(Member.class);

Root<Member> m = query.from(Member.class);

CriteriaQuery<Member> cq = query.select(m);

String username = "sample";
if (username != null) {
    cq.where(cb.equal(m.get("username"), username));
}
em.createQuery(cq).getResultList();

Hibernate: 
    /* <criteria> */ select
        m1_0.MEMBER_ID,
        m1_0.city,
        m1_0.street,
        m1_0.zipcode,
        m1_0.USERNAME 
    from
        Member m1_0 
    where
        m1_0.USERNAME=?
```

다만, 이 역시 로직이 복잡해지고 코드가 길어지면 읽기가 매우 어려워지기 때문에 **`실무에서 사용하지 않습니다.`**

### QueryDSL

```java
JPAFactoryQuery query = new JPAQueryFactory(em); 
QMember m = QMember.member; 

// SQL과 매우 흡사하고 직관적
List<Member> list =  
    query.selectFrom(m) 
         .where(m.age.gt(18)) 
         .orderBy(m.name.desc()) 
         .fetch(); 
```

Criteria처럼 문자가 아닌 자바 코드로  JPQL을 작성할 수 있고 이 역시 JPQL 빌더의 역할을 수행합니다. 자바 코드로 작성하니 당연히 컴파일시에 오류를 잡아낼 수 있고 동적쿼리 작성이 매우 편합니다.

### 네이티브 SQL

JPA가 제공하는 SQL을 직접 사용하는 기능으로 오라클의 CONNECT BY와 같이 JPQL로 해결할 수 없는 특정 DB를 처리하기 위한 기능입니다.

```java
// 그냥 쿼리다.
String sql =  
    “SELECT ID, AGE, TEAM_ID, NAME FROM MEMBER WHERE NAME = ‘kim’";  
List<Member> resultList =  
            em.createNativeQuery(sql, Member.class).getResultList();
```

### JDBC 직접 사용, SPringJdbcTemplate 등

JPA를 사용하면서 JDBC 커넥션을 직접 사용하거나, 스프링 JdbcTemplate, 마이바티스 등을 함께 사용할 수 있습니다. 다만, 직접 사용하니 JPA를 우회해서 SQL을 실행하기 전 영속성 컨텍스트를 적절한 시점에 강제로 플러시 해줘야 합니다.

# JPQL(Java Persistence Query Language)

## 기본 문법

엔티티와 속성은 대소문자를 구분하며 (Member, age) JPQL 키워드는 대소문자를 구분하지 않습니다. 사용시 중요한점은 테이블 이름이 아닌 엔티티의 이름을 사용해야 하며 **`별칭의 사용은 필수`** 입니다.

```java
select_문 :: =  
    select_절 
    from_절 
    [where_절] 
    [groupby_절] 
    [having_절] 
    [orderby_절] 
update_문 :: = update_절 [where_절] 
delete_문 :: = delete_절 [where_절]

// 기본 select 예시
select m from Member m where m.age > 18
```

### 집합과 정렬

```java
select 
	COUNT(m),   //회원수
	SUM(m.age), //나이 합
	AVG(m.age), //평균 나이
	MAX(m.age), //최대 나이
	MIN(m.age)  //최소 나이
from Member m
```

### TypeQuery, Query

- TypeQuery : 타입이 명확함
- Query : 타입이 명확하지 않음

```java

// select m === 타입 확실
TypedQuery<Member> query = em.createQuery("select m from Member m", Member.class);
// username은 String, age는 int === 타입이 확실하지 않음
Query query1 = em.createQuery("select m.username, m.age from Member m");
```

### 결과 조회 API

- query.getResultList() : 결과가 **`하나 이상`**일 때 리스트 반환
    - 결과 없음 : 빈 리스트 반환
- query.getSingleResult(): 결과가 **`정확히 하나`**, 단일 객체 반환
    - 결과 없음 : NoResultExcpetion
    - 둘 이상 : NonUniqueResultException

### 파라미터 바인딩 - 이름 기준, 위치 기준

```java
// 이름 기준 :username
Member result = em.createQuery("select m from Member m where m.username = :username", Member.class)
  .setParameter("username", "member1")
  .getSingleResult();

// 위치 기준 ?1
Member result = em.createQuery("select m from Member m where m.username = ?1", Member.class)
  .setParameter(1, "member1")
  .getSingleResult();

```

위치 기준의 경우 파라미터 순서에 따라 쿼리가 달라질 수 있기 때문에 **`실무에선 사용하지 않습니다`**.

## 프로젝션

JPA에서는 SELECT 절에 조회할 대상은 **`모두 영속성 컨텍스트에 의해 관리`**되기 떄문에 필요한 부분만 지정하는 것으로 엔티티, 임베디드 타입, 스칼라 타입이 됩니다.

- SELECT **`m`** FROM Member m -> 엔티티 프로젝션
- SELECT **`m.team`** FROM Member m -> 엔티티 프로젝션
- SELECT **`m.address`** FROM Member m -> 임베디드 타입 프로젝션
- SELECT **`m.username, m.age`** FROM Member m -> 스칼라 타입 프로젝션
- DISTINCT로 중복 제거

### 여러 값 조회

`SELECT m.username, m.age FROM Member m`

- Query 타입으로 조회
    - `Query query = em.createQuery("select m.username, m.age from Member m", Member.class);`
- Object[] 타입으로 조회

    ```java
    List<Object[]> resultList = em.createQuery("select m.username, m.age from Member m")
                    .getResultList();
    
    Object[] result = resultList.get(0);
    System.out.println("username = " + result[0]);
    System.out.println("age = " + result[1])
    ```

- new 명령어로 조회
    - 단순 값을 DTO로 바로 조회
    - 패키지 명을 포함한 전체 클래스 명 입력
    - 순서와 타입이 일치하는 생성자 필요

        ```java
        em.createQuery("select new jpql.MemberDTO(m.username, m.age) from Member m", MemberDTO.class)
        	.getResultList();
        ```


## 페이징 API

JPA는 페이징을 다음 두 API로 추상화하여 제공합니다.

- setFirstResult(int startPosition) : 조회 시작 위치(0부터 시작)
- setMaxResults(int maxResult) : 조회할 데이터 수

해당 API는 추상화 되어있기 때문에 제공된 dialect에 따라 해당 DB에 맞는 쿼리로 자동 변환되어 나옵니다.

```java
List<Member> result = em.createQuery("select m from Member m order by m.age desc", Member.class)
                    .setFirstResult(0)
                    .setMaxResults(10)
                    .getResultList();
// h2         
Hibernate: 
    /* select
        m 
    from
        Member m 
    order by
        m.age desc */ select
            m1_0.id,
            m1_0.age,
            m1_0.TEAM_ID,
            m1_0.username 
        from
            Member m1_0 
        order by
            m1_0.age desc 
        offset
            ? rows 
        fetch
            first ? rows only
```

## 조인

- 내부 조인: SELECT m FROM Member m [INNER] JOIN [m.team](http://m.team) t
- 외부 조인: SELECT m FROM Member m LEFT [OUTER] JOIN [m.team](http://m.team) t
- 세타 조인: select count(m) from Member m, Team t where m.username = t.name

### ON절

```java
// 조인 대상 필터링
String query = "select m from Member m left join m.team t on t.name = 'teamA'";
        
Hibernate: 
    /* select
        m 
    from
        Member m 
    left join
        m.team t 
            on t.name = 'teamA' */ select
                m1_0.id,
                m1_0.age,
                m1_0.TEAM_ID,
                m1_0.username 
        from
            Member m1_0 
        left join
            Team t1_0 
                on t1_0.id=m1_0.TEAM_ID  // 연관관계에 의한 ID
                and t1_0.name='teamA'
                
                
// 연관관계 없는 엔티티 외부 조인
String query = "select m from Member m left join Team t on m.username = t.name";
Hibernate: 
    /* select
        m 
    from
        Member m 
    left join
        Team t 
            on m.username = t.name */ select
                m1_0.id,
                m1_0.age,
                m1_0.TEAM_ID,
                m1_0.username 
        from
            Member m1_0 
        left join
            Team t1_0 
                on m1_0.username=t1_0.name
```

## 서브 쿼리

일반적인 SQL 작성하듯 JPA 역시 서브 쿼리를 지원하며 아래 서브 쿼리 함수 또한 지원하고 있습니다.

- [NOT] EXISTS (subquery): 서브 쿼리에 결과가 존재하면 참
    - {ALL | ANY | SOME} (subquery)
    - ALL 모두 만족하면 참
    - ANY, SOME : 같은 의미, 조건을 하나라도 만족하면 참
- [NOT] IN (subquery) : 서브 쿼리의 결과 중 하나라도 같은 것이 있으면 참

```java
// teamA인 회원
String query = "select m from Member m " 
                + "where exists (select t from m.team t where t.name = 'teamA')";
Hibernate: 
    /* select
        m 
    from
        Member m 
    where
        exists (select
            t 
        from
            m.team t 
        where
            t.name = 'teamA') */ select
            m1_0.id,
            m1_0.age,
            m1_0.TEAM_ID,
            m1_0.username 
        from
            Member m1_0 
        where
            exists(select
                t2_0.id 
            from
                Team t2_0 
            where
                t2_0.name='teamA' 
                and t2_0.id=m1_0.TEAM_ID)

// 재고보다 주문량이 많은 주문
String query = "select o from Order o"
                + " where o.orderAmount > ALL (select p.stockAmount from Product p)";
Hibernate: 
    /* select
        o 
    from
        
    Order o where
        o.orderAmount > ALL (select
            p.stockAmount 
        from
            Product p) */ select
            o1_0.id,
            o1_0.city,
            o1_0.street,
            o1_0.zipcode,
            o1_0.orderAmount,
            o1_0.PRODUCT_ID 
        from
            ORDERS o1_0 
        where
            o1_0.orderAmount>all(select
                p2_0.stockAmount 
            from
                Product p2_0)
                

// 어떤 팀이든 팀에 소속된 회원
String query = "select m from Member m "
                + "where m.team = ANY (select t from Team t)";
Hibernate: 
    /* select
        m 
    from
        Member m 
    where
        m.team = ANY (select
            t 
        from
            Team t) */ select
            m1_0.id,
            m1_0.age,
            m1_0.TEAM_ID,
            m1_0.username 
        from
            Member m1_0 
        where
            m1_0.TEAM_ID=any(select
                t2_0.id 
            from
                Team t2_0)
```

## 타입 표현

- 문자 : ‘HEELLO’, ‘SHS’’s’
- 숫자 : 10L(Long), 10D(Double), 10F(Float)
- Boolean : TRUE, FASLE
- ENUM : jpabook.MemberType.Admin `(패키지명 반드시 포함)`
- 엔티티 타입: TYPE(m) = Member (상속 관계에서 사용)

## 조건식 - CASE 식

DB Query의 Case 식과 같기 때문에 어려울 것 없이 그냥 쓰면 됩니다.

```java
String query =
"select " +
      "case when m.age <= 10 then '학생요금' " +
      "     when m.age >= 60 then '경로요금' " +
      "     else '일반요금' " +
      "end " +
"from Member m";

Hibernate: 
    /* select
        case 
            when m.age <= 10 
                then '학생요금'      
            when m.age >= 60 
                then '경로요금'      
            else '일반요금' 
        end 
    from
        Member m */ select
            case 
                when m1_0.age<=10 
                    then '학생요금' 
                when m1_0.age>=60 
                    then '경로요금' 
                else '일반요금' 
            end 
        from
            Member m1_0
```

## 함수

JPQL에서 제공하는 기본 함수들로 **`DB에 상관없이`** 편하게 쓸 수 있습니다.

- CONCAT
- SUBSTRING
- TRIM
- LOWER, UPPER
- LENGTH
- LOCATE
- ABS, SQRT, MOD
- SIZE, INDEX(JPA 용도)

**이 링크를 통해 구매하시면 제가 수익을 받을 수 있어요. 🤗**

https://inf.run/4Sbno