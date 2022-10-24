package org.drools.reteoo;

import org.drools.AssertionException;
import org.drools.DroolsTestCase;
import org.drools.FactException;
import org.drools.RetractionException;
import org.drools.rule.Rule;
import org.drools.spi.PropagationContext;

public class ObjectSourceTest extends DroolsTestCase
{

    public void testObjectSourceConstructor()
    {
        MockObjectSource source = new MockObjectSource( 15 );
        assertEquals( 15,
                      source.getId() );

        assertEquals( 0,
                      source.getAttached() );
        source.attach();
        assertEquals( 1,
                      source.getAttached() );
    }

    public void testAddObjectSink()
    {
        MockObjectSource source = new MockObjectSource( 15 );
        assertLength( 0,
                      source.getObjectSinks() );

        source.addObjectSink( new MockObjectSink() );
        assertLength( 1,
                      source.getObjectSinks() );

        source.addObjectSink( new MockObjectSink() );
        assertLength( 2,
                      source.getObjectSinks() );
    }

    public void testPropagateAssertObject() throws Exception
    {
        Rule rule = new Rule( "test-rule" );
        PropagationContext context = new PropagationContextImpl( PropagationContext.ASSERTION,
                                                             null,
                                                             null );
        WorkingMemoryImpl workingMemory = new WorkingMemoryImpl( new RuleBaseImpl( new Rete() ) );

        MockObjectSource source = new MockObjectSource( 15 );
        MockObjectSink sink1 = new MockObjectSink();
        source.addObjectSink( sink1 );
        source.ruleAttached();
        assertLength( 0,
                      sink1.getAsserted() );

        source.propagateAssertObject( new Integer( 1 ),
                                      new FactHandleImpl( 2 ),
                                      context,
                                      workingMemory );

        assertLength( 1,
                      sink1.getAsserted() );

        Object[] list = (Object[]) sink1.getAsserted().get( 0 );
        assertEquals( new Integer( 1 ),
                      list[0] );
        assertEquals( new FactHandleImpl( 2 ),
                      list[1] );

        MockObjectSink sink2 = new MockObjectSink();
        source.addObjectSink( sink2 );
        source.ruleAttached();

        source.propagateAssertObject( new Integer( 2 ),
                                      new FactHandleImpl( 3 ),
                                      context,
                                      workingMemory );

        assertLength( 2,
                      sink1.getAsserted() );

        assertLength( 1,
                      sink2.getAsserted() );

        list = (Object[]) sink1.getAsserted().get( 0 );
        assertEquals( new Integer( 1 ),
                      list[0] );
        assertEquals( new FactHandleImpl( 2 ),
                      list[1] );
        assertSame( context,
                    list[2] );
        assertSame( workingMemory,
                    list[3] );

        list = (Object[]) sink1.getAsserted().get( 1 );
        assertEquals( new Integer( 2 ),
                      list[0] );
        assertEquals( new FactHandleImpl( 3 ),
                      list[1] );
        assertSame( context,
                    list[2] );
        assertSame( workingMemory,
                    list[3] );

        list = (Object[]) sink2.getAsserted().get( 0 );
        assertEquals( new Integer( 2 ),
                      list[0] );
        assertEquals( new FactHandleImpl( 3 ),
                      list[1] );
        assertSame( context,
                    list[2] );
        assertSame( workingMemory,
                    list[3] );
        try
        {
            sink1.setAssertionException( new AssertionException( "test" ) );
            source.propagateAssertObject( new Integer( 2 ),
                                          new FactHandleImpl( 3 ),
                                          context,
                                          workingMemory );
            fail( "Should have thrown 'AssertionException'" );

        }
        catch ( AssertionException e )
        {
            // this exception should be thrown
        }
        catch ( Exception e )
        {
            fail( "Should have thrown 'AssertionException' and not '" + e.getClass() + "'" );
        }
    }

    public void testPropagateRetractObject() throws Exception
    {

        Rule rule = new Rule( "test-rule" );
        PropagationContext context = new PropagationContextImpl( PropagationContext.RETRACTION,
                                                             null,
                                                             null );
        WorkingMemoryImpl workingMemory = new WorkingMemoryImpl( new RuleBaseImpl( new Rete() ) );

        MockObjectSource source = new MockObjectSource( 15 );
        MockObjectSink sink1 = new MockObjectSink();
        source.addObjectSink( sink1 );
        assertLength( 0,
                      sink1.getRetracted() );

        source.propagateRetractObject( new FactHandleImpl( 2 ),
                                       context,
                                       workingMemory );

        assertLength( 1,
                      sink1.getRetracted() );

        Object[] list = (Object[]) sink1.getRetracted().get( 0 );
        assertEquals( new FactHandleImpl( 2 ),
                      list[0] );
        assertSame( context,
                    list[1] );
        assertSame( workingMemory,
                    list[2] );

        MockObjectSink sink2 = new MockObjectSink();
        source.addObjectSink( sink2 );

        source.propagateRetractObject( new FactHandleImpl( 3 ),
                                       context,
                                       workingMemory );

        assertLength( 2,
                      sink1.getRetracted() );

        assertLength( 1,
                      sink2.getRetracted() );

        list = (Object[]) sink1.getRetracted().get( 0 );
        assertEquals( new FactHandleImpl( 2 ),
                      list[0] );
        assertSame( context,
                    list[1] );
        assertSame( workingMemory,
                    list[2] );

        list = (Object[]) sink1.getRetracted().get( 1 );
        assertEquals( new FactHandleImpl( 3 ),
                      list[0] );
        assertSame( context,
                    list[1] );
        assertSame( workingMemory,
                    list[2] );

        list = (Object[]) sink2.getRetracted().get( 0 );
        assertEquals( new FactHandleImpl( 3 ),
                      list[0] );
        assertSame( context,
                    list[1] );
        assertSame( workingMemory,
                    list[2] );

        try
        {
            sink1.setRetractionException( new RetractionException( "test" ) );
            source.propagateRetractObject( new FactHandleImpl( 3 ),
                                           context,
                                           workingMemory );
            fail( "Should have thrown 'RetractionException'" );

        }
        catch ( RetractionException e )
        {

        }
        catch ( Exception e )
        {
            fail( "Should have thrown 'RetractionException' and not '" + e.getClass() + "'" );
        }
    }
    
    public void testPropogateOnAttachRule() throws FactException
    {
        PropagationContext context = new PropagationContextImpl( PropagationContext.ASSERTION,
                                                             null,
                                                             null );
        WorkingMemoryImpl workingMemory = new WorkingMemoryImpl( new RuleBaseImpl( new Rete() ) );
        
        MockObjectSource source = new MockObjectSource( 15 );
 
        MockObjectSink sink1 = new MockObjectSink();
        source.addObjectSink( sink1 );
        source.ruleAttached();

        MockObjectSink sink2 = new MockObjectSink();
        source.addObjectSink( sink2 );
        
        /* We've just added a new node, so should be marked in ruleAttachN mde */
        source.propagateAssertObject( new Integer( 1 ),
                                      new FactHandleImpl( 2 ),
                                      context,
                                      workingMemory );     
        
        /* All sinks except the last one get ignore in propogations during ruleAttach mode */
        assertLength( 0,
                      sink1.getAsserted() );
        assertLength( 1,
                      sink2.getAsserted() ); 

        /* rule is attached and propagation should act as normal */
        source.ruleAttached();
        
        source.propagateAssertObject( new Integer( 2 ),
                                      new FactHandleImpl( 3 ),
                                      context,
                                      workingMemory );     
        
        /* Both sinks receive one object */
        assertLength( 1,
                      sink1.getAsserted() );
        assertLength( 2,
                      sink2.getAsserted() );         
                       
    }
    
}
