library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity FIR_HPF_TB is
end entity FIR_HPF_TB;

architecture test of FIR_HPF_TB is
    -- Test signals
    signal clk : std_logic := '0';
    signal en : std_logic := '1';
    signal output : std_logic_vector(11 downto 0);
    signal finished : std_logic := '0';

    -- Component under test
    component digital_filter
        port (
            CLK : in std_logic;
            EN  : in std_logic;
            OUTPUT : out std_logic_vector(11 downto 0)
        );
    end component;

begin
    -- Instantiate the digital filter system
    DUT: digital_filter
        port map (
            CLK => clk,
            EN => en,
            OUTPUT => output
        );

    -- Clock generation (50 MHz)
    clk_process: process
    begin
        while finished = '0' loop
            clk <= '0';
            wait for 10 ns;
            clk <= '1';
            wait for 10 ns;
        end loop;
        wait;
    end process;

    -- Test stimulus
    stimulus: process
    begin
        -- Reset phase
        en <= '0';
        wait for 100 ns;
        
        -- Enable the filter
        en <= '1';
        wait for 1000 us; -- Run for 1ms to see filtering behavior
        
        -- Test complete
        finished <= '1';
        report "Test completed at " & time'image(now);
        wait;
    end process;

end architecture test;